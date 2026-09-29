import random
from collections.abc import Iterable
from datetime import datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from dibbler.lib.sql_helpers import DEFAULT_STREAMING_ITER_CHUNK_SIZE, iter_in_chunks
from dibbler.models import Product, TransactionLog, TransactionLogProduct, TransactionLogUser, User
from dibbler.models.enums import TransactionLogEntryType
from dibbler.queries import transaction_log, transaction_log_query
from tests.helpers import assert_id_order_similar_to_time_order, assign_times


def _make_user(sql_session: Session, name: str) -> User:
    user = User(name, None, credit=100)
    sql_session.add(user)
    sql_session.flush()
    return user


def _make_product(sql_session: Session, name: str) -> Product:
    product = Product(f"{abs(hash(name)) % 10**12:012d}", name, price=10, stock=10)
    sql_session.add(product)
    sql_session.flush()
    return product


def _trx_entry(
    entry_type: TransactionLogEntryType,
    users: Iterable[User] = (),
    products: Iterable[Product] = (),
    description: str | None = None,
) -> TransactionLog:
    return TransactionLog(
        type=entry_type,
        description=description,
        users={
            TransactionLogUser(
                user=user,
                amount=None if entry_type == TransactionLogEntryType.ADJUST_STOCK else 1,
            )
            for user in users
        },
        products={
            TransactionLogProduct(product=product, amount=1, price_at_time=product.price)
            for product in products
        },
    )


def _buy(users: Iterable[User], products: Iterable[Product]) -> TransactionLog:
    return _trx_entry(TransactionLogEntryType.BUY_PRODUCT, users=users, products=products)


def _add(users: Iterable[User], products: Iterable[Product]) -> TransactionLog:
    return _trx_entry(TransactionLogEntryType.ADD_PRODUCT, users=users, products=products)


def _adjust_stock(user: User, product: Product) -> TransactionLog:
    return _trx_entry(TransactionLogEntryType.ADJUST_STOCK, users=[user], products=[product])


def _transfer(sender: User, receiver: User) -> TransactionLog:
    return _trx_entry(TransactionLogEntryType.TRANSFER, users=[sender, receiver])


def _adjust_balance(user: User) -> TransactionLog:
    return _trx_entry(TransactionLogEntryType.ADJUST_BALANCE, users=[user])


def _insert_trx_entries(sql_session: Session, entries: Iterable[TransactionLog]) -> None:
    for entry in entries:
        sql_session.add(entry)
        sql_session.add_all(entry.users)
        sql_session.add_all(entry.products)
    sql_session.flush()
    sql_session.expire_all()


def _insert_in_order(
    sql_session: Session,
    entries: list[TransactionLog],
    delta: timedelta = timedelta(minutes=1),
) -> list[TransactionLog]:
    assign_times(entries, delta=delta)
    _insert_trx_entries(sql_session, entries)
    assert_id_order_similar_to_time_order(entries)
    return entries


def _insert_shuffled(
    sql_session: Session,
    entries: list[TransactionLog],
    seed: int = 1337,
) -> list[TransactionLog]:
    assign_times(entries)
    shuffled = list(entries)
    random.Random(seed).shuffle(shuffled)
    _insert_trx_entries(sql_session, shuffled)
    return entries


def _generate_a_bunch_of_entries(sql_session: Session, count: int) -> list[TransactionLog]:
    user = _make_user(sql_session, "randomguy")
    return [_adjust_balance(user) for _ in range(count)]


def _ids(entries: Iterable[TransactionLog]) -> list[int]:
    return [e.id for e in entries]


# ----------------------------------------------------


def test_empty_log(sql_session: Session) -> None:
    assert transaction_log(sql_session) == []


def test_streaming(sql_session: Session) -> None:
    limit = 20
    entries = _insert_in_order(sql_session, _generate_a_bunch_of_entries(sql_session, 25))

    streamed = iter_in_chunks(sql_session, transaction_log_query(limit=limit), chunk_size=7)

    newest_first = list(reversed(entries))[:limit]
    assert _ids(streamed) == _ids(reversed(newest_first))


def test_time_order(sql_session: Session) -> None:
    entries = _insert_shuffled(
        sql_session,
        _generate_a_bunch_of_entries(sql_session, 2 * DEFAULT_STREAMING_ITER_CHUNK_SIZE + 1),
    )

    streamed = iter_in_chunks(sql_session, transaction_log_query())

    assert _ids(streamed) == _ids(entries)


def test_equal_time_id_order(sql_session: Session) -> None:
    entries = _generate_a_bunch_of_entries(sql_session, 5)
    for entry in entries:
        entry.time = datetime(2024, 1, 1)
    _insert_trx_entries(sql_session, entries)

    assert _ids(transaction_log(sql_session)) == sorted(_ids(entries))


def test_insertion_order_ignored(sql_session: Session) -> None:
    entries = _insert_shuffled(sql_session, _generate_a_bunch_of_entries(sql_session, 25))

    assert _ids(transaction_log(sql_session)) == _ids(entries)
    assert _ids(entries) != sorted(_ids(entries))


def test_newest_first(sql_session: Session) -> None:
    entries = _insert_shuffled(sql_session, _generate_a_bunch_of_entries(sql_session, 10))

    result = transaction_log(sql_session, newest_first=True)

    assert _ids(result) == _ids(reversed(entries))


def test_newest_first_equal_time_reverse_id_order(sql_session: Session) -> None:
    entries = _generate_a_bunch_of_entries(sql_session, 5)
    for entry in entries:
        entry.time = datetime(2024, 1, 1)
    _insert_trx_entries(sql_session, entries)

    result = transaction_log(sql_session, newest_first=True)

    assert _ids(result) == sorted(_ids(entries), reverse=True)


def test_newest_first_with_limit(sql_session: Session) -> None:
    entries = _insert_shuffled(sql_session, _generate_a_bunch_of_entries(sql_session, 10), seed=7)

    result = transaction_log(sql_session, limit=3, newest_first=True)

    assert _ids(result) == _ids(reversed(entries[-3:]))


def test_children_loaded(sql_session: Session) -> None:
    alice = _make_user(sql_session, "alice")
    bob = _make_user(sql_session, "bob")
    chips = _make_product(sql_session, "chips")
    _insert_in_order(
        sql_session,
        [
            _buy([alice, bob], [chips]),
        ],
    )

    (entry,) = transaction_log(sql_session)

    assert {u.user.name for u in entry.users} == {"alice", "bob"}
    assert {p.product.name for p in entry.products} == {"chips"}


def test_user_filter(sql_session: Session) -> None:
    alice = _make_user(sql_session, "alice")
    bob = _make_user(sql_session, "bob")
    carl = _make_user(sql_session, "carl")
    a, ab, b = _insert_in_order(
        sql_session,
        [
            _adjust_balance(alice),
            _transfer(alice, bob),
            _adjust_balance(bob),
        ],
    )

    assert _ids(transaction_log(sql_session, user=alice)) == [a.id, ab.id]
    assert _ids(transaction_log(sql_session, user=bob)) == [ab.id, b.id]
    assert _ids(transaction_log(sql_session, user=carl)) == []


def test_user_filter_no_duplicates(sql_session: Session) -> None:
    alice = _make_user(sql_session, "alice")
    chips = _make_product(sql_session, "chips")
    (entry,) = _insert_in_order(
        sql_session,
        [_buy([alice, alice], [chips])],
    )

    assert _ids(transaction_log(sql_session, user=alice)) == [entry.id]


def test_product_filter(sql_session: Session) -> None:
    alice = _make_user(sql_session, "alice")
    chips = _make_product(sql_session, "chips")
    soda = _make_product(sql_session, "soda")
    c, cs, s, _ = _insert_in_order(
        sql_session,
        [
            _buy([alice], [chips]),
            _buy([alice], [chips, soda]),
            _adjust_stock(alice, soda),
            _adjust_balance(alice),
        ],
    )

    assert _ids(transaction_log(sql_session, product=chips)) == [c.id, cs.id]
    assert _ids(transaction_log(sql_session, product=soda)) == [cs.id, s.id]


def test_entry_type_filter(sql_session: Session) -> None:
    alice = _make_user(sql_session, "alice")
    bob = _make_user(sql_session, "bob")
    chips = _make_product(sql_session, "chips")
    buy, add, transfer = _insert_in_order(
        sql_session,
        [
            _buy([alice], [chips]),
            _add([alice], [chips]),
            _transfer(alice, bob),
        ],
    )

    only_buy = transaction_log(sql_session, entry_type=[TransactionLogEntryType.BUY_PRODUCT])
    assert _ids(only_buy) == [buy.id]

    buy_or_transfer = transaction_log(
        sql_session,
        entry_type=[TransactionLogEntryType.BUY_PRODUCT, TransactionLogEntryType.TRANSFER],
    )
    assert _ids(buy_or_transfer) == [buy.id, transfer.id]

    negated = transaction_log(
        sql_session,
        entry_type=[TransactionLogEntryType.BUY_PRODUCT],
        negate_entry_type_filter=True,
    )
    assert _ids(negated) == [add.id, transfer.id]

    assert _ids(transaction_log(sql_session, entry_type=[])) == []
    assert _ids(transaction_log(sql_session, entry_type=[], negate_entry_type_filter=True)) == [
        buy.id,
        add.id,
        transfer.id,
    ]


def test_time_filter(sql_session: Session) -> None:
    entries = _insert_in_order(sql_session, _generate_a_bunch_of_entries(sql_session, 5))

    after = transaction_log(sql_session, after_time=entries[2].time)
    assert _ids(after) == _ids(entries[2:])

    before = transaction_log(sql_session, before_time=entries[2].time)
    assert _ids(before) == _ids(entries[:2])

    window = transaction_log(
        sql_session,
        after_time=entries[1].time,
        before_time=entries[3].time,
    )
    assert _ids(window) == _ids(entries[1:3])


def test_equal_time_bounds_give_empty_range(sql_session: Session) -> None:
    entries = _insert_in_order(sql_session, _generate_a_bunch_of_entries(sql_session, 3))

    result = transaction_log(
        sql_session,
        after_time=entries[1].time,
        before_time=entries[1].time,
    )

    assert result == []


def test_time_range_is_inclusive_exclusive(sql_session: Session) -> None:
    entries = _generate_a_bunch_of_entries(sql_session, 5)
    day = datetime(2024, 3, 15)
    entries[0].time = day - timedelta(microseconds=1)
    entries[1].time = day
    entries[2].time = day + timedelta(hours=12)
    entries[3].time = day + timedelta(days=1) - timedelta(microseconds=1)
    entries[4].time = day + timedelta(days=1)
    _insert_trx_entries(sql_session, entries)

    result = transaction_log(
        sql_session,
        after_time=day,
        before_time=day + timedelta(days=1),
    )

    assert _ids(result) == _ids(entries[1:4])


def test_limit(sql_session: Session) -> None:
    entries = _insert_shuffled(sql_session, _generate_a_bunch_of_entries(sql_session, 20))

    assert _ids(transaction_log(sql_session, limit=5)) == _ids(entries[15:])


def test_limit_larger_than_log(sql_session: Session) -> None:
    entries = _insert_in_order(sql_session, _generate_a_bunch_of_entries(sql_session, 3))

    assert _ids(transaction_log(sql_session, limit=100)) == _ids(entries)


def test_limit_across_streamed_chunks(sql_session: Session) -> None:
    chunk_size = DEFAULT_STREAMING_ITER_CHUNK_SIZE
    extra = chunk_size // 2
    limit = chunk_size + extra
    entries = _insert_in_order(
        sql_session,
        _generate_a_bunch_of_entries(sql_session, 2 * chunk_size + extra),
    )

    streamed = iter_in_chunks(sql_session, transaction_log_query(limit=limit))

    newest_first = list(reversed(entries))[:limit]
    assert _ids(streamed) == _ids(reversed(newest_first))


def test_limit_after_filters(sql_session: Session) -> None:
    alice = _make_user(sql_session, "alice")
    bob = _make_user(sql_session, "bob")
    mine = _insert_in_order(
        sql_session,
        [
            *(_adjust_balance(alice) for _ in range(3)),
            *(_adjust_balance(bob) for _ in range(3)),
        ],
    )[:3]

    assert _ids(transaction_log(sql_session, user=alice, limit=2)) == _ids(mine[1:])


def test_combined_filters(sql_session: Session) -> None:
    alice = _make_user(sql_session, "alice")
    bob = _make_user(sql_session, "bob")
    carl = _make_user(sql_session, "carl")
    chips = _make_product(sql_session, "chips")
    too_early, hit, _wrong_type, _wrong_user = _insert_in_order(
        sql_session,
        [
            _transfer(alice, bob),
            _transfer(alice, bob),
            _buy([alice], [chips]),
            _transfer(bob, carl),
        ],
    )

    result = transaction_log(
        sql_session,
        user=alice,
        entry_type=[TransactionLogEntryType.TRANSFER],
        after_time=hit.time,
    )

    assert too_early.time < hit.time
    assert _ids(result) == [hit.id]


def test_user_and_product_rejected(sql_session: Session) -> None:
    user = _make_user(sql_session, "alice")
    product = _make_product(sql_session, "chips")

    with pytest.raises(ValueError, match="both user and product"):
        transaction_log(sql_session, user=user, product=product)


def test_inverted_time_range_rejected(sql_session: Session) -> None:
    with pytest.raises(ValueError, match="after_time"):
        transaction_log(
            sql_session,
            after_time=datetime(2024, 1, 2),
            before_time=datetime(2024, 1, 1),
        )


@pytest.mark.parametrize("limit", [0, -1])
def test_non_positive_limit_rejected(sql_session: Session, limit: int) -> None:
    with pytest.raises(ValueError, match="Limit must be positive"):
        transaction_log(sql_session, limit=limit)

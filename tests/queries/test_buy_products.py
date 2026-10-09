import math

import pytest
from sqlalchemy.orm import Session

from dibbler.models import Product, TransactionLog, User
from dibbler.models.enums import TransactionLogEntryType
from dibbler.queries import buy_products
from dibbler.queries.buy_products import MAX_BUY_AMOUNT_TOTAL

DEFAULT_PEPSI_STOCK = 10
DEFAULT_PEPSI_PRICE = 15


def _make_product(
    sql_session: Session,
    barcode: str = "1234567890",
    name: str = "Pepsi",
    stock: int = DEFAULT_PEPSI_STOCK,
    price: int = DEFAULT_PEPSI_PRICE,
) -> Product:
    product = Product(barcode, name, price, stock=stock)
    sql_session.add(product)
    sql_session.flush()
    return product


def _make_user(sql_session: Session, name: str, credit: int = 100) -> User:
    user = User(name, None, credit=credit)
    sql_session.add(user)
    sql_session.flush()
    return user


def test_buy_products_charges_a_single_buyer_and_decrements_stock(sql_session: Session) -> None:
    product = _make_product(sql_session)
    alice = _make_user(sql_session, "alice", credit=100)
    amount = 3

    buy_products(sql_session, [(alice, 1)], [(product, amount)])

    sql_session.expire_all()

    assert alice.credit == 100 - amount * DEFAULT_PEPSI_PRICE
    assert product.stock == DEFAULT_PEPSI_STOCK - amount


def test_buy_products_with_expired_buyers_and_products(sql_session: Session) -> None:
    product = _make_product(sql_session)
    alice = _make_user(sql_session, "alice", credit=100)
    bob = _make_user(sql_session, "bob", credit=100)
    amount = 2

    sql_session.expire_all()

    buy_products(sql_session, [(alice, 1), (bob, 1)], [(product, amount)])

    sql_session.expire_all()

    buyer_share = math.ceil(amount * DEFAULT_PEPSI_PRICE / 2)
    assert alice.credit == 100 - buyer_share
    assert bob.credit == 100 - buyer_share
    assert product.stock == DEFAULT_PEPSI_STOCK - amount


def test_buy_products_charges_each_share_with_its_penalty(sql_session: Session) -> None:
    product = _make_product(sql_session, price=10)
    alice = _make_user(sql_session, "alice")
    bob = _make_user(sql_session, "bob")
    carol = _make_user(sql_session, "carol")

    buy_products(sql_session, [(alice, 1), (bob, 1), (carol, 2)], [(product, 1)])

    sql_session.expire_all()

    base_share = math.ceil(10 / 3)
    assert alice.credit == 100 - base_share
    assert bob.credit == 100 - base_share
    assert carol.credit == 100 - base_share * 2


def test_buy_products_updates_multiple_products_independently(sql_session: Session) -> None:
    cola = _make_product(sql_session, barcode="1111111111", name="Cola", stock=10, price=15)
    pepsi = _make_product(sql_session, barcode="2222222222", name="Pepsi", stock=4, price=8)
    alice = _make_user(sql_session, "alice")

    buy_products(sql_session, [(alice, 1)], [(cola, 2), (pepsi, 3)])

    sql_session.expire_all()

    assert cola.stock == 8
    assert pepsi.stock == 1
    assert alice.credit == 100 - (2 * 15 + 3 * 8)


def test_buy_products_allows_a_repeated_buyer_alongside_another_buyer(
    sql_session: Session,
) -> None:
    product = _make_product(sql_session, price=12)
    alice = _make_user(sql_session, "alice")
    bob = _make_user(sql_session, "bob")

    buy_products(sql_session, [(alice, 1), (alice, 1), (bob, 2)], [(product, 1)])

    sql_session.expire_all()

    buyer_share = math.ceil(12 / 3)

    # 2 buyer shares for alice
    assert alice.credit == 100 - 2 * buyer_share

    # 1 buyer share for bob, but multiplied by his penalty of 2
    assert bob.credit == 100 - buyer_share * 2

    log = sql_session.query(TransactionLog).one()
    assert len(log.users) == 3
    assert {share.user for share in log.users} == {alice, bob}


@pytest.mark.parametrize(
    ("price", "buyers", "expected_charges", "expected_transactions"),
    [
        pytest.param(
            11,
            [("alice", 1), ("alice", 1)],
            {"alice": 11},
            [("alice", 1)],
            id="single-repeated-buyer",
        ),
        pytest.param(
            13,
            [("alice", 1), ("bob", 2), ("alice", 1), ("bob", 2)],
            {"alice": 7, "bob": 14},
            [("alice", 1), ("bob", 2)],
            id="2x2",
        ),
    ],
)
def test_buy_products_simplifies_buyer_shares_by_their_gcd(
    sql_session: Session,
    price: int,
    buyers: list[tuple[str, int]],
    expected_charges: dict[str, int],
    expected_transactions: list[tuple[str, int]],
) -> None:
    product = _make_product(sql_session, price=price)
    users = {name: _make_user(sql_session, name) for name in expected_charges}

    buy_products(
        sql_session,
        [(users[name], penalty) for name, penalty in buyers],
        [(product, 1)],
    )

    sql_session.expire_all()

    log = sql_session.query(TransactionLog).one()
    assert {name: 100 - user.credit for name, user in users.items()} == expected_charges
    assert sorted((share.user.name, share.penalty) for share in log.users) == expected_transactions


def test_buy_products_records_a_transaction_log_entry(sql_session: Session) -> None:
    product = _make_product(sql_session)
    alice = _make_user(sql_session, "alice")
    bob = _make_user(sql_session, "bob")

    buy_products(sql_session, [(alice, 1), (bob, 2)], [(product, 5)])

    sql_session.expire_all()

    log = sql_session.query(TransactionLog).one()
    assert log.type == TransactionLogEntryType.BUY_PRODUCT
    assert sorted((share.user.name, share.amount, share.penalty) for share in log.users) == [
        ("alice", 38, 1),
        ("bob", 76, 2),
    ]
    assert [(entry.product, entry.amount, entry.price_at_time) for entry in log.products] == [
        (product, -5, DEFAULT_PEPSI_PRICE),
    ]


def test_buy_products_allows_buying_the_max_amount_in_total(sql_session: Session) -> None:
    cola = _make_product(sql_session, barcode="1111111111", name="Cola")
    pepsi = _make_product(sql_session, barcode="2222222222", name="Pepsi")
    alice = _make_user(sql_session, "alice")

    buy_products(sql_session, [(alice, 1)], [(cola, MAX_BUY_AMOUNT_TOTAL - 1), (pepsi, 1)])

    sql_session.expire_all()

    assert cola.stock == DEFAULT_PEPSI_STOCK - (MAX_BUY_AMOUNT_TOTAL - 1)
    assert pepsi.stock == DEFAULT_PEPSI_STOCK - 1


@pytest.mark.parametrize(
    ("penalties", "amounts", "error"),
    [
        pytest.param([], [1], "At least one buyer", id="no-buyers"),
        pytest.param([0], [1], "Penalty must be at least 1", id="zero-penalty"),
        pytest.param([-1], [1], "Penalty must be at least 1", id="negative-penalty"),
        pytest.param([1, 2], [1], "cannot have more than one penalty", id="inconsistent-penalty"),

        pytest.param([1], [], "At least one product", id="no-products"),
        pytest.param([1], [0], "Product amounts must be positive", id="zero-amount"),
        pytest.param([1], [-1], "Product amounts must be positive", id="negative-amount"),
        pytest.param([1], [1, 0], "Product amounts must be positive", id="valid-amount-zero-amount"),
        pytest.param([1], [MAX_BUY_AMOUNT_TOTAL + 1], "Total product amount must be at most", id="too-large-amount"),
        pytest.param([1], [MAX_BUY_AMOUNT_TOTAL, 1], "Total product amount must be at most", id="too-large-total-amount"),
    ],
)  # fmt: skip
def test_invariants(
    sql_session: Session,
    penalties: list[int],
    amounts: list[int],
    error: str,
) -> None:
    product = _make_product(sql_session)
    alice = _make_user(sql_session, "alice", credit=100)

    with pytest.raises(ValueError, match=error):
        buy_products(
            sql_session,
            [(alice, penalty) for penalty in penalties],
            [(product, amount) for amount in amounts],
        )

    sql_session.expire_all()

    assert alice.credit == 100
    assert product.stock == DEFAULT_PEPSI_STOCK
    assert sql_session.query(TransactionLog).count() == 0

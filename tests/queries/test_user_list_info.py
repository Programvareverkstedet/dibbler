from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from dibbler.lib.sql_helpers import iter_rows_in_chunks
from dibbler.models import Product, TransactionLog, User
from dibbler.queries import (
    add_stock,
    adjust_balance,
    adjust_stock,
    buy_products,
    transfer,
    user_info,
    user_list_info,
    user_list_info_query,
)
from dibbler.queries.user_info import UserInfo
from dibbler.queries.user_list_info import UserListInfo


def _make_product(sql_session: Session, bar_code: str, name: str) -> Product:
    product = Product(bar_code, name, 10, stock=100)
    sql_session.add(product)
    sql_session.flush()
    return product


def _make_user(sql_session: Session, name: str) -> User:
    user = User(name, None, credit=1000)
    sql_session.add(user)
    sql_session.flush()
    return user


def _set_last_entry_time(sql_session: Session, time: datetime) -> None:
    entry = sql_session.scalars(
        select(TransactionLog).order_by(TransactionLog.id.desc()).limit(1),
    ).one()
    entry.time = time
    sql_session.flush()


def _add(sql_session: Session, users: list[User], product: Product, amount: int) -> None:
    add_stock(sql_session, users, [(product, amount, amount * 10)], total_price=amount * 10)


# ---------------------------------------------


def test_no_activity(sql_session: Session) -> None:
    alice = _make_user(sql_session, "alice")
    bob = _make_user(sql_session, "bob")

    assert user_list_info(sql_session) == [
        UserListInfo(alice, 0, 0, None),
        UserListInfo(bob, 0, 0, None),
    ]


def test_includes_every_user_ordered_by_name(sql_session: Session) -> None:
    pepsi = _make_product(sql_session, "1111111111", "Pepsi")
    charlie = _make_user(sql_session, "charlie")
    alice = _make_user(sql_session, "alice")
    dave = _make_user(sql_session, "dave")
    bob = _make_user(sql_session, "bob")

    buy_products(sql_session, [(dave, 1)], [(pepsi, 1)])
    adjust_balance(sql_session, bob, 10)

    assert [row.user for row in user_list_info(sql_session)] == [alice, bob, charlie, dave]


def test_matches_user_info(sql_session: Session) -> None:
    pepsi = _make_product(sql_session, "1111111111", "Pepsi")
    cola = _make_product(sql_session, "2222222222", "Cola")
    alice = _make_user(sql_session, "alice")
    bob = _make_user(sql_session, "bob")
    charlie = _make_user(sql_session, "charlie")
    dave = _make_user(sql_session, "dave")
    eve = _make_user(sql_session, "eve")

    buy_products(sql_session, [(alice, 1)], [(pepsi, 2), (cola, 3)])
    _set_last_entry_time(sql_session, datetime(2024, 1, 1))
    buy_products(sql_session, [(alice, 1), (bob, 2)], [(pepsi, 4)])
    _set_last_entry_time(sql_session, datetime(2024, 1, 2))
    _add(sql_session, [bob], cola, 5)
    _set_last_entry_time(sql_session, datetime(2024, 1, 3))
    _add(sql_session, [alice, charlie], pepsi, 6)
    _set_last_entry_time(sql_session, datetime(2024, 1, 4))
    adjust_stock(sql_session, dave, cola, -2)
    _set_last_entry_time(sql_session, datetime(2024, 1, 5))
    transfer(sql_session, charlie, dave, 10)
    _set_last_entry_time(sql_session, datetime(2024, 1, 6))
    adjust_balance(sql_session, bob, 10)
    _set_last_entry_time(sql_session, datetime(2024, 1, 7))

    rows = user_list_info(sql_session)

    assert rows == [
        UserListInfo(alice, 9, 6, datetime(2024, 1, 4)),
        UserListInfo(bob, 4, 5, datetime(2024, 1, 7)),
        UserListInfo(charlie, 0, 6, datetime(2024, 1, 6)),
        UserListInfo(dave, 0, 0, datetime(2024, 1, 6)),
        UserListInfo(eve, 0, 0, None),
    ]

    for row in rows:
        user_info_result = user_info(sql_session, row.user)
        assert (
            row.last_activity,
            row.products_bought,
            row.products_added,
        ) == (
            user_info_result.last_activity,
            user_info_result.products_bought,
            user_info_result.products_added,
        ), row.user.name


def test_user_listed_twice_in_trx(sql_session: Session) -> None:
    pepsi = _make_product(sql_session, "1111111111", "Pepsi")
    alice = _make_user(sql_session, "alice")

    _add(sql_session, [alice, alice], pepsi, 3)
    _set_last_entry_time(sql_session, datetime(2024, 1, 1))

    assert user_list_info(sql_session) == [UserListInfo(alice, 0, 3, datetime(2024, 1, 1))]
    assert user_info(sql_session, alice) == UserInfo(datetime(2024, 1, 1), 0, 3, 0, 0)


def test_streaming(sql_session: Session) -> None:
    pepsi = _make_product(sql_session, "1111111111", "Pepsi")
    users = [_make_user(sql_session, f"user{i:02d}") for i in range(25)]
    for i, user in enumerate(users):
        buy_products(sql_session, [(user, 1)], [(pepsi, i + 1)])

    query = user_list_info_query()
    streamed = [tuple(row) for row in iter_rows_in_chunks(sql_session, query, chunk_size=7)]

    assert streamed == user_list_info(sql_session)
    assert [row[:3] for row in streamed] == [(user, i + 1, 0) for i, user in enumerate(users)]

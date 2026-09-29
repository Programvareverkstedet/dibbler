from datetime import datetime

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from dibbler.models import Product, TransactionLog, User
from dibbler.queries import (
    add_stock,
    adjust_balance,
    adjust_stock,
    buy_products,
    transfer,
    user_info,
)
from dibbler.queries.user_info import UserInfo


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

    assert user_info(sql_session, alice) == UserInfo(None, 0, 0)


def test_last_activity(sql_session: Session) -> None:
    pepsi = _make_product(sql_session, "1111111111", "Pepsi")
    alice = _make_user(sql_session, "alice")
    bob = _make_user(sql_session, "bob")

    buy_products(sql_session, [(alice, 1)], [(pepsi, 1)])
    _set_last_entry_time(sql_session, datetime(2024, 1, 3))
    adjust_balance(sql_session, alice, 10)
    _set_last_entry_time(sql_session, datetime(2024, 1, 1))

    assert user_info(sql_session, alice).last_activity == datetime(2024, 1, 3)

    transfer(sql_session, bob, alice, 10)
    _set_last_entry_time(sql_session, datetime(2024, 1, 5))

    assert user_info(sql_session, alice).last_activity == datetime(2024, 1, 5)


def test_last_activity_ignores_other_users(sql_session: Session) -> None:
    pepsi = _make_product(sql_session, "1111111111", "Pepsi")
    alice = _make_user(sql_session, "alice")
    bob = _make_user(sql_session, "bob")

    buy_products(sql_session, [(alice, 1)], [(pepsi, 1)])
    _set_last_entry_time(sql_session, datetime(2024, 1, 1))
    buy_products(sql_session, [(bob, 1)], [(pepsi, 1)])
    _set_last_entry_time(sql_session, datetime(2024, 1, 2))

    assert user_info(sql_session, alice).last_activity == datetime(2024, 1, 1)


def test_product_sum(sql_session: Session) -> None:
    pepsi = _make_product(sql_session, "1111111111", "Pepsi")
    cola = _make_product(sql_session, "2222222222", "Cola")
    alice = _make_user(sql_session, "alice")

    buy_products(sql_session, [(alice, 1)], [(pepsi, 2), (cola, 3)])
    buy_products(sql_session, [(alice, 1)], [(pepsi, 1)])
    _add(sql_session, [alice], cola, 4)
    _add(sql_session, [alice], pepsi, 5)

    info = user_info(sql_session, alice)

    assert (info.products_bought, info.products_added) == (6, 9)


def test_product_sum_ignore_other_users(sql_session: Session) -> None:
    pepsi = _make_product(sql_session, "1111111111", "Pepsi")
    alice = _make_user(sql_session, "alice")
    bob = _make_user(sql_session, "bob")

    buy_products(sql_session, [(alice, 1)], [(pepsi, 1)])
    buy_products(sql_session, [(bob, 1)], [(pepsi, 2)])
    _add(sql_session, [bob], pepsi, 3)

    info = user_info(sql_session, alice)

    assert (info.products_bought, info.products_added) == (1, 0)


def test_product_sum_count_shared_entries_for_each_user(sql_session: Session) -> None:
    pepsi = _make_product(sql_session, "1111111111", "Pepsi")
    alice = _make_user(sql_session, "alice")
    bob = _make_user(sql_session, "bob")

    buy_products(sql_session, [(alice, 1), (bob, 1)], [(pepsi, 2)])
    _add(sql_session, [alice, bob], pepsi, 6)

    for user in (alice, bob):
        info = user_info(sql_session, user)
        assert (info.products_bought, info.products_added) == (2, 6)


def test_activity_without_products(sql_session: Session) -> None:
    alice = _make_user(sql_session, "alice")

    adjust_balance(sql_session, alice, 10)
    _set_last_entry_time(sql_session, datetime(2024, 1, 1))

    assert user_info(sql_session, alice) == UserInfo(datetime(2024, 1, 1), 0, 0)


def test_time_filter(sql_session: Session) -> None:
    pepsi = _make_product(sql_session, "1111111111", "Pepsi")
    alice = _make_user(sql_session, "alice")

    buy_products(sql_session, [(alice, 1)], [(pepsi, 1)])
    _set_last_entry_time(sql_session, datetime(2024, 1, 1))
    buy_products(sql_session, [(alice, 1)], [(pepsi, 2)])
    _set_last_entry_time(sql_session, datetime(2024, 1, 2))
    _add(sql_session, [alice], pepsi, 4)
    _set_last_entry_time(sql_session, datetime(2024, 1, 3))

    assert user_info(
        sql_session,
        alice,
        after_time=datetime(2024, 1, 2),
    ) == UserInfo(datetime(2024, 1, 3), 2, 4)

    assert user_info(
        sql_session,
        alice,
        before_time=datetime(2024, 1, 2),
    ) == UserInfo(datetime(2024, 1, 1), 1, 0)

    assert user_info(
        sql_session,
        alice,
        after_time=datetime(2024, 1, 2),
        before_time=datetime(2024, 1, 3),
    ) == UserInfo(datetime(2024, 1, 2), 2, 0)

    assert user_info(
        sql_session,
        alice,
        after_time=datetime(2024, 1, 4),
    ) == UserInfo(None, 0, 0)


def test_invalid_time_range(sql_session: Session) -> None:
    alice = _make_user(sql_session, "alice")

    with pytest.raises(ValueError, match="after_time"):
        user_info(
            sql_session,
            alice,
            after_time=datetime(2024, 1, 2),
            before_time=datetime(2024, 1, 1),
        )

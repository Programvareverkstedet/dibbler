from datetime import datetime

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from dibbler.models import Product, TransactionLog, User
from dibbler.queries import (
    add_stock,
    adjust_stock,
    buy_products,
    merge_products,
    product_info,
)
from dibbler.queries.product_info import ProductInfo


def _make_product(sql_session: Session, barcode: str, name: str) -> Product:
    product = Product(barcode, name, 10, stock=100)
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
    pepsi = _make_product(sql_session, "1111111111", "Pepsi")

    assert product_info(sql_session, pepsi) == ProductInfo(None, 0, 0, 0, 0)


def test_last_activity(sql_session: Session) -> None:
    pepsi = _make_product(sql_session, "1111111111", "Pepsi")
    alice = _make_user(sql_session, "alice")

    buy_products(sql_session, [(alice, 1)], [(pepsi, 1)])
    _set_last_entry_time(sql_session, datetime(2024, 1, 3))
    _add(sql_session, [alice], pepsi, 2)
    _set_last_entry_time(sql_session, datetime(2024, 1, 1))

    assert product_info(sql_session, pepsi).last_activity == datetime(2024, 1, 3)

    adjust_stock(sql_session, alice, pepsi, -1)
    _set_last_entry_time(sql_session, datetime(2024, 1, 5))

    assert product_info(sql_session, pepsi).last_activity == datetime(2024, 1, 5)


def test_last_activity_ignores_other_products(sql_session: Session) -> None:
    pepsi = _make_product(sql_session, "1111111111", "Pepsi")
    cola = _make_product(sql_session, "2222222222", "Cola")
    alice = _make_user(sql_session, "alice")

    buy_products(sql_session, [(alice, 1)], [(pepsi, 1)])
    _set_last_entry_time(sql_session, datetime(2024, 1, 1))
    buy_products(sql_session, [(alice, 1)], [(cola, 1)])
    _set_last_entry_time(sql_session, datetime(2024, 1, 2))

    assert product_info(sql_session, pepsi).last_activity == datetime(2024, 1, 1)


def test_product_sum(sql_session: Session) -> None:
    pepsi = _make_product(sql_session, "1111111111", "Pepsi")
    cola = _make_product(sql_session, "2222222222", "Cola")
    alice = _make_user(sql_session, "alice")
    bob = _make_user(sql_session, "bob")

    buy_products(sql_session, [(alice, 1)], [(pepsi, 2), (cola, 3)])
    buy_products(sql_session, [(bob, 1)], [(pepsi, 1)])
    _add(sql_session, [alice], pepsi, 5)
    _add(sql_session, [bob], cola, 4)
    adjust_stock(sql_session, alice, pepsi, -7)

    info = product_info(sql_session, pepsi)

    assert (info.times_bought, info.times_added) == (3, 5)


def test_product_sum_counts_shared_entries_once(sql_session: Session) -> None:
    pepsi = _make_product(sql_session, "1111111111", "Pepsi")
    alice = _make_user(sql_session, "alice")
    bob = _make_user(sql_session, "bob")

    buy_products(sql_session, [(alice, 1), (alice, 1), (bob, 1)], [(pepsi, 2)])
    _add(sql_session, [alice, bob], pepsi, 6)

    info = product_info(sql_session, pepsi)

    assert (info.times_bought, info.times_added) == (2, 6)


def test_product_sum_includes_merged_products(sql_session: Session) -> None:
    pepsi = _make_product(sql_session, "1111111111", "Pepsi")
    pepsi_max = _make_product(sql_session, "2222222222", "Pepsi Max")
    alice = _make_user(sql_session, "alice")

    buy_products(sql_session, [(alice, 1)], [(pepsi, 2)])
    buy_products(sql_session, [(alice, 1)], [(pepsi_max, 3)])
    _add(sql_session, [alice], pepsi_max, 4)

    merge_products(sql_session, alice, pepsi_max, pepsi)

    info = product_info(sql_session, pepsi)

    assert (info.times_bought, info.times_added) == (5, 4)


def test_time_filter(sql_session: Session) -> None:
    pepsi = _make_product(sql_session, "1111111111", "Pepsi")
    alice = _make_user(sql_session, "alice")

    buy_products(sql_session, [(alice, 1)], [(pepsi, 1)])
    _set_last_entry_time(sql_session, datetime(2024, 1, 1))
    buy_products(sql_session, [(alice, 1)], [(pepsi, 2)])
    _set_last_entry_time(sql_session, datetime(2024, 1, 2))
    _add(sql_session, [alice], pepsi, 4)
    _set_last_entry_time(sql_session, datetime(2024, 1, 3))

    assert product_info(
        sql_session,
        pepsi,
        after_time=datetime(2024, 1, 2),
    ) == ProductInfo(datetime(2024, 1, 3), 2, 4, 0, 0)

    assert product_info(
        sql_session,
        pepsi,
        before_time=datetime(2024, 1, 2),
    ) == ProductInfo(datetime(2024, 1, 1), 1, 0, 0, 0)

    assert product_info(
        sql_session,
        pepsi,
        after_time=datetime(2024, 1, 2),
        before_time=datetime(2024, 1, 3),
    ) == ProductInfo(datetime(2024, 1, 2), 2, 0, 0, 0)

    assert product_info(
        sql_session,
        pepsi,
        after_time=datetime(2024, 1, 4),
    ) == ProductInfo(None, 0, 0, 0, 0)


def test_invalid_time_range(sql_session: Session) -> None:
    pepsi = _make_product(sql_session, "1111111111", "Pepsi")

    with pytest.raises(ValueError, match="after_time"):
        product_info(
            sql_session,
            pepsi,
            after_time=datetime(2024, 1, 2),
            before_time=datetime(2024, 1, 1),
        )


def test_stock_adjustments(sql_session: Session) -> None:
    pepsi = _make_product(sql_session, "1111111111", "Pepsi")
    cola = _make_product(sql_session, "2222222222", "Cola")
    alice = _make_user(sql_session, "alice")
    bob = _make_user(sql_session, "bob")

    buy_products(sql_session, [(alice, 1)], [(pepsi, 4)])
    _add(sql_session, [alice], pepsi, 6)
    adjust_stock(sql_session, alice, pepsi, -7)
    adjust_stock(sql_session, bob, pepsi, 2)
    adjust_stock(sql_session, bob, cola, 3)

    info = product_info(sql_session, pepsi)

    assert (info.stock_adjustments, info.stock_adjustment_sum) == (2, -5)
    assert pepsi.stock == 100 - info.times_bought + info.times_added + info.stock_adjustment_sum


def test_stock_adjustments_time_filter(sql_session: Session) -> None:
    pepsi = _make_product(sql_session, "1111111111", "Pepsi")
    alice = _make_user(sql_session, "alice")

    adjust_stock(sql_session, alice, pepsi, -7)
    _set_last_entry_time(sql_session, datetime(2024, 1, 1))
    adjust_stock(sql_session, alice, pepsi, 2)
    _set_last_entry_time(sql_session, datetime(2024, 1, 2))

    assert product_info(
        sql_session,
        pepsi,
        after_time=datetime(2024, 1, 2),
    ) == ProductInfo(datetime(2024, 1, 2), 0, 0, 1, 2)

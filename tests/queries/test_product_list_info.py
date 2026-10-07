from datetime import datetime

import pytest
from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from dibbler.models import Product, ProductBarcode, TransactionLog, User
from dibbler.queries import (
    add_stock,
    adjust_balance,
    adjust_stock,
    buy_products,
    product_info,
    product_list_info,
    product_list_info_stream,
)
from dibbler.queries.product_list_info import ProductListInfo


def _make_product(
    sql_session: Session,
    barcode: str,
    name: str,
    stock: int = 100,
    hidden: bool = False,
) -> Product:
    product = Product(barcode, name, 10, stock=stock, hidden=hidden)
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


def test_no_products(sql_session: Session) -> None:
    assert product_list_info(sql_session) == []
    assert list(product_list_info_stream(sql_session)) == []


def test_no_activity(sql_session: Session) -> None:
    pepsi = _make_product(sql_session, "1111111111", "Pepsi")

    assert product_list_info(sql_session) == [ProductListInfo(pepsi, 0, 0, None)]


@pytest.mark.parametrize(
    ("include_hidden", "include_zero_stock", "expected"),
    [
        (False, True, ["Pepsi", "Fanta"]),
        (True, True, ["Pepsi", "Cola", "Fanta", "Solo", "Urge"]),
        (False, False, ["Pepsi"]),
        (True, False, ["Pepsi", "Cola", "Urge"]),
    ],
)
def test_include_flags(
    sql_session: Session,
    include_hidden: bool,
    include_zero_stock: bool,
    expected: list[str],
) -> None:
    _make_product(sql_session, "1111111111", "Pepsi", stock=5)
    _make_product(sql_session, "2222222222", "Cola", stock=3, hidden=True)
    _make_product(sql_session, "3333333333", "Fanta", stock=0)
    _make_product(sql_session, "4444444444", "Solo", stock=0, hidden=True)
    _make_product(sql_session, "5555555555", "Urge", stock=-2, hidden=True)

    rows = product_list_info(
        sql_session,
        include_hidden=include_hidden,
        include_zero_stock=include_zero_stock,
    )
    streamed = product_list_info_stream(
        sql_session,
        include_hidden=include_hidden,
        include_zero_stock=include_zero_stock,
        chunk_size=2,
    )

    assert [row.product.name for row in rows] == expected
    assert list(streamed) == rows


def test_ordered_by_stock_then_id(sql_session: Session) -> None:
    pepsi = _make_product(sql_session, "1111111111", "Pepsi", stock=1)
    cola = _make_product(sql_session, "2222222222", "Cola", stock=10)
    fanta = _make_product(sql_session, "3333333333", "Fanta", stock=-3)
    solo = _make_product(sql_session, "4444444444", "Solo", stock=10)

    assert [row.product for row in product_list_info(sql_session)] == [cola, solo, pepsi, fanta]


def test_matches_product_info(sql_session: Session) -> None:
    pepsi = _make_product(sql_session, "1111111111", "Pepsi")
    cola = _make_product(sql_session, "2222222222", "Cola")
    fanta = _make_product(sql_session, "3333333333", "Fanta")
    solo = _make_product(sql_session, "4444444444", "Solo")
    alice = _make_user(sql_session, "alice")
    bob = _make_user(sql_session, "bob")

    buy_products(sql_session, [(alice, 1)], [(pepsi, 2), (cola, 3)])
    _set_last_entry_time(sql_session, datetime(2024, 1, 1))
    buy_products(sql_session, [(alice, 1), (bob, 2)], [(pepsi, 4)])
    _set_last_entry_time(sql_session, datetime(2024, 1, 2))
    _add(sql_session, [bob], cola, 5)
    _set_last_entry_time(sql_session, datetime(2024, 1, 3))
    adjust_stock(sql_session, alice, fanta, -2)
    _set_last_entry_time(sql_session, datetime(2024, 1, 4))
    adjust_balance(sql_session, bob, 10)
    _set_last_entry_time(sql_session, datetime(2024, 1, 5))

    rows = product_list_info(sql_session)

    # Stock: cola 102, solo 100, fanta 98, pepsi 94
    assert rows == [
        ProductListInfo(cola, 3, 5, datetime(2024, 1, 3)),
        ProductListInfo(solo, 0, 0, None),
        ProductListInfo(fanta, 0, 0, datetime(2024, 1, 4)),
        ProductListInfo(pepsi, 6, 0, datetime(2024, 1, 2)),
    ]

    for row in rows:
        product_info_result = product_info(sql_session, row.product)
        assert (
            row.last_activity,
            row.times_bought,
            row.times_added,
        ) == (
            product_info_result.last_activity,
            product_info_result.times_bought,
            product_info_result.times_added,
        ), row.product.name


def test_loads_barcodes(sql_session: Session) -> None:
    pepsi = _make_product(sql_session, "1111111111", "Pepsi")
    pepsi.barcodes.add(ProductBarcode(code="5555555555"))
    sql_session.flush()
    sql_session.expire_all()

    [row] = product_list_info_stream(sql_session)

    assert "barcodes" not in inspect(row.product).unloaded
    assert {bc.code for bc in row.product.barcodes} == {"1111111111", "5555555555"}


def test_streaming(sql_session: Session) -> None:
    alice = _make_user(sql_session, "alice")
    products = [
        _make_product(sql_session, f"{i:010d}", f"Product {i:02d}", stock=100 - i)
        for i in range(25)
    ]
    for i, product in enumerate(products):
        buy_products(sql_session, [(alice, 1)], [(product, i + 1)])

    streamed = list(product_list_info_stream(sql_session, chunk_size=7))

    assert streamed == product_list_info(sql_session)
    assert [row[:3] for row in streamed] == [
        (product, i + 1, 0) for i, product in enumerate(products)
    ]

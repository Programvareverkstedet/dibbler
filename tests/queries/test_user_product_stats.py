from datetime import datetime

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from dibbler.lib.sql_helpers import iter_rows_in_chunks
from dibbler.models import Product, TransactionLog, User
from dibbler.queries import (
    add_stock,
    buy_products,
    merge_products,
    user_product_stats,
    user_product_stats_query,
)
from dibbler.queries.user_product_stats import UserProductStats


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


# ----------------------------------------------


def test_empty(sql_session: Session) -> None:
    alice = _make_user(sql_session, "alice")

    assert user_product_stats(sql_session, alice) == []


def test_summing_multiple_purchases(sql_session: Session) -> None:
    pepsi = _make_product(sql_session, "1111111111", "Pepsi")
    cola = _make_product(sql_session, "2222222222", "Cola")
    alice = _make_user(sql_session, "alice")

    buy_products(sql_session, [(alice, 1)], [(pepsi, 2), (cola, 1)])
    buy_products(sql_session, [(alice, 1)], [(pepsi, 3)])

    assert user_product_stats(sql_session, alice) == [(pepsi, 5, 0), (cola, 1, 0)]


def test_summing_multiple_add_stocks(sql_session: Session) -> None:
    pepsi = _make_product(sql_session, "1111111111", "Pepsi")
    alice = _make_user(sql_session, "alice")

    _add(sql_session, [alice], pepsi, 10)
    _add(sql_session, [alice], pepsi, 5)
    buy_products(sql_session, [(alice, 1)], [(pepsi, 2)])

    assert user_product_stats(sql_session, alice) == [UserProductStats(pepsi, 2, 15)]


def test_order_by_count(sql_session: Session) -> None:
    pepsi = _make_product(sql_session, "1111111111", "Pepsi")
    cola = _make_product(sql_session, "2222222222", "Cola")
    solo = _make_product(sql_session, "3333333333", "Solo")
    fanta = _make_product(sql_session, "4444444444", "Fanta")
    alice = _make_user(sql_session, "alice")

    buy_products(sql_session, [(alice, 1)], [(pepsi, 1), (cola, 1), (solo, 3)])
    _add(sql_session, [alice], cola, 4)
    _add(sql_session, [alice], fanta, 7)

    assert user_product_stats(sql_session, alice) == [
        (solo, 3, 0),
        (cola, 1, 4),
        (pepsi, 1, 0),
        (fanta, 0, 7),
    ]


def test_ignores_other_users(sql_session: Session) -> None:
    pepsi = _make_product(sql_session, "1111111111", "Pepsi")
    cola = _make_product(sql_session, "2222222222", "Cola")
    alice = _make_user(sql_session, "alice")
    bob = _make_user(sql_session, "bob")

    buy_products(sql_session, [(alice, 1)], [(pepsi, 1)])
    buy_products(sql_session, [(bob, 1)], [(cola, 4)])
    _add(sql_session, [bob], pepsi, 3)

    assert user_product_stats(sql_session, alice) == [(pepsi, 1, 0)]
    assert user_product_stats(sql_session, bob) == [(cola, 4, 0), (pepsi, 0, 3)]


def test_shared_entries(sql_session: Session) -> None:
    pepsi = _make_product(sql_session, "1111111111", "Pepsi")
    alice = _make_user(sql_session, "alice")
    bob = _make_user(sql_session, "bob")

    buy_products(sql_session, [(alice, 1), (bob, 1)], [(pepsi, 2)])
    _add(sql_session, [alice, bob], pepsi, 6)

    assert user_product_stats(sql_session, alice) == [(pepsi, 2, 6)]
    assert user_product_stats(sql_session, bob) == [(pepsi, 2, 6)]


def test_product_merge(sql_session: Session) -> None:
    pepsi = _make_product(sql_session, "1111111111", "Pepsi")
    pepsi_max = _make_product(sql_session, "2222222222", "Pepsi Max")
    alice = _make_user(sql_session, "alice")

    buy_products(sql_session, [(alice, 1)], [(pepsi, 2)])
    buy_products(sql_session, [(alice, 1)], [(pepsi_max, 3)])
    _add(sql_session, [alice], pepsi_max, 4)
    merge_products(sql_session, pepsi_max, pepsi)

    assert user_product_stats(sql_session, alice) == [(pepsi, 5, 4)]


def test_time_filter(sql_session: Session) -> None:
    pepsi = _make_product(sql_session, "1111111111", "Pepsi")
    alice = _make_user(sql_session, "alice")

    buy_products(sql_session, [(alice, 1)], [(pepsi, 1)])
    _set_last_entry_time(sql_session, datetime(2024, 1, 1))
    buy_products(sql_session, [(alice, 1)], [(pepsi, 2)])
    _set_last_entry_time(sql_session, datetime(2024, 1, 2))
    _add(sql_session, [alice], pepsi, 4)
    _set_last_entry_time(sql_session, datetime(2024, 1, 3))

    assert user_product_stats(
        sql_session,
        alice,
        after_time=datetime(2024, 1, 2),
    ) == [(pepsi, 2, 4)]

    assert user_product_stats(
        sql_session,
        alice,
        before_time=datetime(2024, 1, 2),
    ) == [(pepsi, 1, 0)]

    assert user_product_stats(
        sql_session,
        alice,
        after_time=datetime(2024, 1, 2),
        before_time=datetime(2024, 1, 3),
    ) == [(pepsi, 2, 0)]

    assert not user_product_stats(
        sql_session,
        alice,
        after_time=datetime(2024, 1, 4),
    )


def test_limit(sql_session: Session) -> None:
    pepsi = _make_product(sql_session, "1111111111", "Pepsi")
    cola = _make_product(sql_session, "2222222222", "Cola")
    solo = _make_product(sql_session, "3333333333", "Solo")
    alice = _make_user(sql_session, "alice")

    buy_products(sql_session, [(alice, 1)], [(pepsi, 3), (cola, 2), (solo, 1)])

    assert user_product_stats(sql_session, alice, limit=2) == [(pepsi, 3, 0), (cola, 2, 0)]


def test_invalid_time_range(sql_session: Session) -> None:
    alice = _make_user(sql_session, "alice")

    with pytest.raises(ValueError, match="after_time"):
        user_product_stats(
            sql_session,
            alice,
            after_time=datetime(2024, 1, 2),
            before_time=datetime(2024, 1, 1),
        )


def test_invalid_limit(sql_session: Session) -> None:
    alice = _make_user(sql_session, "alice")

    with pytest.raises(ValueError, match="Limit"):
        user_product_stats(sql_session, alice, limit=0)


def test_streaming(sql_session: Session) -> None:
    alice = _make_user(sql_session, "alice")
    products = [_make_product(sql_session, f"{i:010d}", f"product{i:02d}") for i in range(25)]
    buy_products(sql_session, [(alice, 1)], [(p, i + 1) for i, p in enumerate(products)])

    query = user_product_stats_query(user=alice, limit=20)
    streamed = [tuple(row) for row in iter_rows_in_chunks(sql_session, query, chunk_size=7)]

    assert streamed == user_product_stats(sql_session, alice, limit=20)
    assert streamed == [(p, i + 1, 0) for i, p in reversed(list(enumerate(products)))][:20]

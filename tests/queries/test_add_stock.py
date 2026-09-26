import math

import pytest
from sqlalchemy.orm import Session

from dibbler.models import Product, User
from dibbler.queries import add_stock


def _make_product(
    sql_session: Session,
    bar_code: str = "1234567890",
    stock: int = 10,
    price: int = 15,
    hidden: bool = False,
) -> Product:
    product = Product(bar_code, "Pepsi 1.5L", price, stock=stock, hidden=hidden)
    sql_session.add(product)
    sql_session.flush()
    return product


def _make_user(sql_session: Session, name: str, credit: int = 0) -> User:
    user = User(name, None, credit=credit)
    sql_session.add(user)
    sql_session.flush()
    return user


def test_add_stock_recomputes_price_stock_and_unhides_product(sql_session: Session) -> None:
    product = _make_product(sql_session, stock=10, price=15, hidden=True)
    alice = _make_user(sql_session, "alice")

    add_stock(sql_session, [alice], [(product, 5, 100)], total_price=100)

    sql_session.expire_all()

    assert product.price == math.ceil(((10 * 15) + 100) / (10 + 5))
    assert product.stock == 15
    assert product.hidden is False


def test_add_stock_floors_stock_at_added_amount_when_starting_negative(
    sql_session: Session,
) -> None:
    product = _make_product(sql_session, stock=-3)
    alice = _make_user(sql_session, "alice")

    add_stock(sql_session, [alice], [(product, 5, 50)], total_price=50)

    sql_session.expire_all()

    assert product.stock == 5


def test_add_stock_splits_total_price_evenly_across_users(sql_session: Session) -> None:
    product = _make_product(sql_session)
    alice = _make_user(sql_session, "alice", credit=0)
    bob = _make_user(sql_session, "bob", credit=0)

    add_stock(sql_session, [alice, bob], [(product, 1, 100)], total_price=100)

    sql_session.expire_all()

    assert alice.credit == 50
    assert bob.credit == 50


def test_add_stock_gives_the_rounding_remainder_to_every_credited_user(
    sql_session: Session,
) -> None:
    # Quirk from original implementation of Purchase.perform_soft_purchase,
    # undivisible splits are rounded up for each user
    product = _make_product(sql_session)
    users = [_make_user(sql_session, name) for name in ("alice", "bob", "carol")]

    add_stock(sql_session, users, [(product, 1, 100)], total_price=100)

    sql_session.expire_all()

    assert [u.credit for u in users] == [34, 34, 34]


def test_add_stock_updates_multiple_products_independently(sql_session: Session) -> None:
    cola = _make_product(sql_session, bar_code="1111111111", stock=10, price=15)
    pepsi = _make_product(sql_session, bar_code="2222222222", stock=4, price=8)
    alice = _make_user(sql_session, "alice")

    purchase = add_stock(
        sql_session,
        [alice],
        [(cola, 5, 100), (pepsi, 2, 20)],
        total_price=100,
    )

    sql_session.expire_all()

    assert cola.stock == 15
    assert cola.price == math.ceil(((10 * 15) + 100) / (10 + 5))
    assert pepsi.stock == 6
    assert pepsi.price == math.ceil(((4 * 8) + 20) / (4 + 2))
    assert {entry.product for entry in purchase.entries} == {cola, pepsi}
    assert {(entry.product, entry.amount) for entry in purchase.entries} == {
        (cola, -5),
        (pepsi, -2),
    }


def test_add_stock_records_a_purchase_linking_entries_and_transactions(
    sql_session: Session,
) -> None:
    product = _make_product(sql_session)
    alice = _make_user(sql_session, "alice")
    bob = _make_user(sql_session, "bob")

    purchase = add_stock(
        sql_session,
        [alice, bob],
        [(product, 5, 100)],
        total_price=100,
        description="restocked",
    )

    sql_session.expire_all()

    assert [entry.product for entry in purchase.entries] == [product]
    assert [entry.amount for entry in purchase.entries] == [-5]
    assert {t.user for t in purchase.transactions} == {alice, bob}
    assert all(t.description == "restocked" for t in purchase.transactions)


def test_add_stock_rejects_no_users(sql_session: Session) -> None:
    product = _make_product(sql_session)

    with pytest.raises(ValueError, match="At least one user"):
        add_stock(sql_session, [], [(product, 5, 100)], total_price=100)


def test_add_stock_rejects_no_products(sql_session: Session) -> None:
    alice = _make_user(sql_session, "alice")

    with pytest.raises(ValueError, match="At least one product"):
        add_stock(sql_session, [alice], [], total_price=100)


def test_add_stock_allows_crediting_nothing_for_stock_received_for_free(
    sql_session: Session,
) -> None:
    product = _make_product(sql_session)
    alice = _make_user(sql_session, "alice", credit=100)

    add_stock(sql_session, [alice], [(product, 5, 0)], total_price=0)

    sql_session.expire_all()

    assert alice.credit == 100
    assert product.stock == 15


def test_add_stock_rejects_negative_total_price(sql_session: Session) -> None:
    product = _make_product(sql_session)
    alice = _make_user(sql_session, "alice")

    with pytest.raises(ValueError, match="Total price must not be negative"):
        add_stock(sql_session, [alice], [(product, 5, 100)], total_price=-1)


def test_add_stock_rejects_non_positive_product_amount(sql_session: Session) -> None:
    product = _make_product(sql_session)
    alice = _make_user(sql_session, "alice")

    with pytest.raises(ValueError, match="Product amounts must be positive"):
        add_stock(sql_session, [alice], [(product, 0, 100)], total_price=100)

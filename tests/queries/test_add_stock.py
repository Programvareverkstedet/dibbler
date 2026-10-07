import math

import pytest
from sqlalchemy.orm import Session

from dibbler.models import Product, ProductLog, TransactionLog, TransactionLogProduct, User
from dibbler.models.enums import ProductLogEntryType, TransactionLogEntryType
from dibbler.queries import add_stock, adjust_stock
from dibbler.queries.add_stock import NEGATIVE_STOCK_RESET_DESCRIPTION


def _make_product(
    sql_session: Session,
    barcode: str = "1234567890",
    stock: int = 10,
    price: int = 15,
    hidden: bool = False,
) -> Product:
    product = Product(barcode, "Pepsi 1.5L", price, stock=stock, hidden=hidden)
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


def test_add_stock_with_expired_users_and_products(sql_session: Session) -> None:
    product = _make_product(sql_session, stock=10, price=15)
    alice = _make_user(sql_session, "alice")
    bob = _make_user(sql_session, "bob")

    sql_session.expire_all()

    add_stock(sql_session, [alice, bob], [(product, 5, 100)], total_price=100)

    sql_session.expire_all()

    assert alice.credit == 50
    assert bob.credit == 50
    assert product.stock == 15


def test_add_stock_floors_stock_at_added_amount_when_starting_negative(
    sql_session: Session,
) -> None:
    product = _make_product(sql_session, stock=-3)
    alice = _make_user(sql_session, "alice")

    add_stock(sql_session, [alice], [(product, 5, 50)], total_price=50)

    sql_session.expire_all()

    assert product.stock == 5


def test_add_stock_logs_resetting_negative_stock(sql_session: Session) -> None:
    product = _make_product(sql_session, stock=-3, price=15)
    alice = _make_user(sql_session, "alice")
    bob = _make_user(sql_session, "bob")

    add_stock(sql_session, [alice, bob], [(product, 5, 50)], total_price=50)

    sql_session.expire_all()

    reset = (
        sql_session.query(TransactionLog)
        .filter(TransactionLog.type == TransactionLogEntryType.ADJUST_STOCK)
        .one()
    )
    assert reset.description == NEGATIVE_STOCK_RESET_DESCRIPTION
    assert [(u.user, u.amount) for u in reset.users] == [(alice, None)]
    assert [(p.product, p.amount, p.price_at_time) for p in reset.products] == [(product, 3, 15)]


def test_add_stock_does_not_reset_non_negative_stock(sql_session: Session) -> None:
    product = _make_product(sql_session, stock=0)
    alice = _make_user(sql_session, "alice")

    add_stock(sql_session, [alice], [(product, 5, 50)], total_price=50)

    sql_session.expire_all()

    assert sql_session.query(TransactionLog).one().type == TransactionLogEntryType.ADD_PRODUCT


@pytest.mark.parametrize("stock", [-3, 0, 4])
def test_add_stock_keeps_log_sum_equal_to_stock(sql_session: Session, stock: int) -> None:
    product = _make_product(sql_session, stock=0)
    alice = _make_user(sql_session, "alice")
    if stock:
        adjust_stock(sql_session, alice, product, stock)

    add_stock(sql_session, [alice], [(product, 5, 50)], total_price=50)

    sql_session.expire_all()

    logged = sum(
        x.amount
        for x in sql_session.query(TransactionLogProduct).filter(
            TransactionLogProduct.product_id == product.id,
        )
    )
    assert logged == product.stock


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
    cola = _make_product(sql_session, barcode="1111111111", stock=10, price=15)
    pepsi = _make_product(sql_session, barcode="2222222222", stock=4, price=8)
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


def test_add_stock_records_a_transaction_log_entry(sql_session: Session) -> None:
    product = _make_product(sql_session)
    alice = _make_user(sql_session, "alice")

    add_stock(sql_session, [alice], [(product, 5, 100)], total_price=100)

    sql_session.expire_all()

    log = sql_session.query(TransactionLog).one()
    assert log.type == TransactionLogEntryType.ADD_PRODUCT


def test_add_stock_logs_unhiding_a_hidden_product(sql_session: Session) -> None:
    product = _make_product(sql_session, hidden=True)
    alice = _make_user(sql_session, "alice")

    add_stock(sql_session, [alice], [(product, 5, 100)], total_price=100)

    sql_session.expire_all()

    header = sql_session.query(TransactionLog).one()
    edit = sql_session.query(ProductLog).filter(ProductLog.type == ProductLogEntryType.EDIT).one()
    assert edit.product_id == product.id
    assert edit.hidden is False
    assert edit.name is None
    assert edit.price is None
    assert edit.time == header.time


def test_add_stock_does_not_log_an_edit_for_a_visible_product(sql_session: Session) -> None:
    product = _make_product(sql_session, hidden=False)
    alice = _make_user(sql_session, "alice")

    add_stock(sql_session, [alice], [(product, 5, 100)], total_price=100)

    sql_session.expire_all()

    assert (
        sql_session.query(ProductLog).filter(ProductLog.type == ProductLogEntryType.EDIT).count()
        == 0
    )


def test_add_stock_allows_crediting_nothing_for_stock_received_for_free(
    sql_session: Session,
) -> None:
    product = _make_product(sql_session)
    alice = _make_user(sql_session, "alice", credit=100)

    add_stock(sql_session, [alice], [(product, 5, 0)], total_price=0)

    sql_session.expire_all()

    assert alice.credit == 100
    assert product.stock == 15


@pytest.mark.parametrize(
    ("with_user", "products", "total_price", "description", "error"),
    [
        pytest.param(False, [(5, 100)], 100, None, "At least one user", id="no-users"),

        pytest.param(True, [(5, 100)], -1, None, "Total price must not be negative", id="negative-total-price"),

        pytest.param(True, [(5, 100)], 100, "x" * (TransactionLog.description_length + 1), "Description must be at most", id="too-long-description"),

        pytest.param(True, [], 100, None, "At least one product", id="no-products"),
        pytest.param(True, [(0, 100)], 100, None, "Product amounts must be positive", id="zero-amount"),
        pytest.param(True, [(-1, 100)], 100, None, "Product amounts must be positive", id="negative-amount"),
        pytest.param(True, [(5, 100), (0, 100)], 100, None, "Product amounts must be positive", id="valid-amount-zero-amount"),
        pytest.param(True, [(5, -1)], 0, None, "Paid amounts must not be negative", id="negative-paid-amount"),
        pytest.param(True, [(5, 100), (5, -1)], 100, None, "Paid amounts must not be negative", id="valid-paid-amount-negative-paid-amount"),
    ],
)  # fmt: skip
def test_invariants(
    sql_session: Session,
    with_user: bool,
    products: list[tuple[int, int]],
    total_price: int,
    description: str | None,
    error: str,
) -> None:
    product = _make_product(sql_session, stock=10, price=15)
    alice = _make_user(sql_session, "alice", credit=0)
    users = [alice] if with_user else []

    with pytest.raises(ValueError, match=error):
        add_stock(
            sql_session,
            users,
            [(product, amount, paid_amount) for amount, paid_amount in products],
            total_price=total_price,
            description=description,
        )

    sql_session.expire_all()

    assert alice.credit == 0
    assert (product.stock, product.price) == (10, 15)
    assert sql_session.query(TransactionLog).count() == 0

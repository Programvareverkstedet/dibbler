import pytest
from sqlalchemy.orm import Session

from dibbler.models import Product, ProductLog, TransactionLog, User
from dibbler.models.enums import ProductLogEntryType, TransactionLogEntryType
from dibbler.queries import create_product


def _make_user(sql_session: Session) -> User:
    user = User("alice", None)
    sql_session.add(user)
    sql_session.flush()
    return user


def test_create_product_persists_a_queryable_product(sql_session: Session) -> None:
    alice = _make_user(sql_session)
    product = create_product(
        sql_session,
        "1234567890",
        "Cola",
        15,
        stock=10,
        hidden=True,
        user=alice,
    )

    sql_session.expire_all()

    fetched = sql_session.get(Product, product.id)
    assert fetched is not None
    assert {bc.code for bc in fetched.barcodes} == {"1234567890"}
    assert fetched.name == "Cola"
    assert fetched.price == 15
    assert fetched.stock == 10
    assert fetched.hidden is True


def test_create_product_defaults_to_zero_stock_and_not_hidden(sql_session: Session) -> None:
    product = create_product(sql_session, "1234567890", "Cola", 15)

    sql_session.expire_all()

    assert product.stock == 0
    assert product.hidden is False


def test_create_product_records_a_create_log_entry(sql_session: Session) -> None:
    product = create_product(sql_session, "1234567890", "Cola", 15, hidden=True)

    sql_session.expire_all()

    log = sql_session.query(ProductLog).filter(ProductLog.type == ProductLogEntryType.CREATE).one()
    assert log.product_id == product.id
    assert log.bar_code is None
    assert log.name == "Cola"
    assert log.price == 15
    assert log.hidden is True

    log = (
        sql_session.query(ProductLog)
        .filter(ProductLog.type == ProductLogEntryType.ADD_BARCODE)
        .one()
    )
    assert log.product_id == product.id
    assert log.bar_code == "1234567890"


def test_create_product_records_initial_stock_as_a_stock_adjustment(sql_session: Session) -> None:
    alice = _make_user(sql_session)
    product = create_product(sql_session, "1234567890", "Cola", 15, stock=10, user=alice)

    sql_session.expire_all()

    log = sql_session.query(TransactionLog).one()
    assert log.type == TransactionLogEntryType.ADJUST_STOCK
    assert [(u.user, u.amount) for u in log.users] == [(alice, None)]
    assert [(p.product, p.amount) for p in log.products] == [(product, 10)]


def test_create_product_without_stock_records_no_transaction(sql_session: Session) -> None:
    create_product(sql_session, "1234567890", "Cola", 15)

    sql_session.expire_all()

    assert sql_session.query(TransactionLog).count() == 0


@pytest.mark.parametrize(
    ("bar_code", "name", "price", "stock", "error"),
    [
        pytest.param("", "Pepsi", 20, 0, "Barcode cannot be empty", id="empty-bar-code"),
        pytest.param("123abc", "Pepsi", 20, 0, "digits only", id="non-digit-bar-code"),
        pytest.param("1" * (Product.bar_code_length + 1), "Pepsi", 20, 0, "Barcode must be at most", id="too-long-bar-code"),
        pytest.param("1234567890", "Pepsi", 20, 0, "already in use", id="duplicate-bar-code"),

        pytest.param("0987654321", "", 20, 0, "Name cannot be empty", id="empty-name"),
        pytest.param("0987654321", "Pep\nsi", 20, 0, "Name has an invalid format", id="invalid-chars-name"),
        pytest.param("0987654321", "x" * (Product.name_length + 1), 20, 0, "Name must be at most", id="too-long-name"),

        pytest.param("0987654321", "Pepsi", -3, 0, "Price must be positive", id="negative-price"),
        pytest.param("0987654321", "Pepsi", 0, 0, "Price must be positive", id="non-positive-price"),

        pytest.param("0987654321", "Pepsi", 20, 10, "user is required", id="stock-without-user"),
    ],
)  # fmt: skip
def test_invariants(
    sql_session: Session,
    bar_code: str,
    name: str,
    price: int,
    stock: int,
    error: str,
) -> None:
    create_product(sql_session, "1234567890", "Cola", 15)

    with pytest.raises(ValueError, match=error):
        create_product(sql_session, bar_code, name, price, stock)

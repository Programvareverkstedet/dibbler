import pytest
from sqlalchemy.orm import Session

from dibbler.models import Product, ProductLog
from dibbler.models.enums import ProductLogEntryType
from dibbler.queries import create_product


def test_create_product_persists_a_queryable_product(sql_session: Session) -> None:
    product = create_product(sql_session, "1234567890", "Cola", 15, stock=10, hidden=True)

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
    product = create_product(sql_session, "1234567890", "Cola", 15, stock=10, hidden=True)

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


@pytest.mark.parametrize(
    ("bar_code", "name", "price", "error"),
    [
        pytest.param("", "Pepsi", 20, "Barcode cannot be empty", id="empty-bar-code"),
        pytest.param("123abc", "Pepsi", 20, "digits only", id="non-digit-bar-code"),
        pytest.param("1" * (Product.bar_code_length + 1), "Pepsi", 20, "Barcode must be at most", id="too-long-bar-code"),
        pytest.param("1234567890", "Pepsi", 20, "already in use", id="duplicate-bar-code"),

        pytest.param("0987654321", "", 20, "Name cannot be empty", id="empty-name"),
        pytest.param("0987654321", "x" * (Product.name_length + 1), 20, "Name must be at most", id="too-long-name"),

        pytest.param("0987654321", "Pepsi", -3, "Price must be positive", id="negative-price"),
        pytest.param("0987654321", "Pepsi", 0, "Price must be positive", id="non-positive-price"),
    ],
)  # fmt: skip
def test_invariants(
    sql_session: Session,
    bar_code: str,
    name: str,
    price: int,
    error: str,
) -> None:
    create_product(sql_session, "1234567890", "Cola", 15)

    with pytest.raises(ValueError, match=error):
        create_product(sql_session, bar_code, name, price)

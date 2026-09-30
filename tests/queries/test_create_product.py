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


def test_create_product_rejects_empty_bar_code(sql_session: Session) -> None:
    with pytest.raises(ValueError, match="Barcode cannot be empty"):
        create_product(sql_session, "", "Cola", 15)


def test_create_product_rejects_empty_name(sql_session: Session) -> None:
    with pytest.raises(ValueError, match="Name cannot be empty"):
        create_product(sql_session, "1234567890", "", 15)


def test_create_product_rejects_non_positive_price(sql_session: Session) -> None:
    with pytest.raises(ValueError, match="Price must be positive"):
        create_product(sql_session, "1234567890", "Cola", 0)


def test_create_product_rejects_non_digit_bar_code(sql_session: Session) -> None:
    with pytest.raises(ValueError, match="digits only"):
        create_product(sql_session, "123abc", "Cola", 15)


def test_create_product_rejects_duplicate_bar_code(sql_session: Session) -> None:
    create_product(sql_session, "1234567890", "Cola", 15)

    with pytest.raises(ValueError, match="already in use"):
        create_product(sql_session, "1234567890", "Pepsi", 20)


def test_create_product_rejects_too_long_bar_code(sql_session: Session) -> None:
    with pytest.raises(ValueError, match="Barcode must be at most"):
        create_product(sql_session, "1" * (Product.bar_code_length + 1), "Cola", 15)


def test_create_product_rejects_too_long_name(sql_session: Session) -> None:
    with pytest.raises(ValueError, match="Name must be at most"):
        create_product(sql_session, "1234567890", "x" * (Product.name_length + 1), 15)

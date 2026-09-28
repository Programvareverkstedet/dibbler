import pytest
from sqlalchemy.orm import Session

from dibbler.models import Product, ProductLog
from dibbler.models.enums import ProductLogEntryType
from dibbler.queries import add_bar_code, create_product, remove_bar_code


def _make_product(sql_session: Session) -> Product:
    product = Product("1234567890", "Cola", 15, stock=10, hidden=False)
    sql_session.add(product)
    sql_session.flush()
    return product


def test_removes_the_given_code(sql_session: Session) -> None:
    product = _make_product(sql_session)
    add_bar_code(sql_session, product, "0987654321")

    remove_bar_code(sql_session, product, "1234567890")

    sql_session.expire_all()

    assert {bc.code for bc in product.barcodes} == {"0987654321"}


def test_records_a_log_entry(sql_session: Session) -> None:
    product = _make_product(sql_session)
    add_bar_code(sql_session, product, "0987654321")

    remove_bar_code(sql_session, product, "0987654321")

    sql_session.expire_all()

    log = (
        sql_session.query(ProductLog)
        .filter(ProductLog.type == ProductLogEntryType.REMOVE_BARCODE)
        .one()
    )
    assert log.product_id == product.id
    assert log.bar_code == "0987654321"


def test_rejects_removing_the_last_code(sql_session: Session) -> None:
    product = _make_product(sql_session)

    with pytest.raises(ValueError, match="last barcode"):
        remove_bar_code(sql_session, product, "1234567890")


def test_rejects_unknown_code(sql_session: Session) -> None:
    product = _make_product(sql_session)
    add_bar_code(sql_session, product, "0987654321")

    with pytest.raises(ValueError, match="not found"):
        remove_bar_code(sql_session, product, "1111111111")


def test_rejects_empty_code(sql_session: Session) -> None:
    product = _make_product(sql_session)
    add_bar_code(sql_session, product, "0987654321")

    with pytest.raises(ValueError, match="cannot be empty"):
        remove_bar_code(sql_session, product, "")


def test_freed_code_can_be_used_by_another_product(sql_session: Session) -> None:
    product = _make_product(sql_session)
    add_bar_code(sql_session, product, "0987654321")
    remove_bar_code(sql_session, product, "0987654321")

    other = create_product(sql_session, "0987654321", "Pepsi", 20)

    sql_session.expire_all()

    assert {bc.code for bc in other.barcodes} == {"0987654321"}

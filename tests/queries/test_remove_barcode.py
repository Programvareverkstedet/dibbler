import pytest
from sqlalchemy.orm import Session

from dibbler.models import Product, ProductLog
from dibbler.models.enums import ProductLogEntryType
from dibbler.queries import add_barcode, create_product, remove_barcode


def _make_product(sql_session: Session) -> Product:
    return create_product(sql_session, "1234567890", "Cola", 15)


def test_removes_the_given_code(sql_session: Session) -> None:
    product = _make_product(sql_session)
    add_barcode(sql_session, product, "0987654321")

    remove_barcode(sql_session, product, "1234567890")

    sql_session.expire_all()

    assert {bc.code for bc in product.barcodes} == {"0987654321"}


def test_records_a_log_entry(sql_session: Session) -> None:
    product = _make_product(sql_session)
    add_barcode(sql_session, product, "0987654321")

    remove_barcode(sql_session, product, "0987654321")

    sql_session.expire_all()

    log = (
        sql_session.query(ProductLog)
        .filter(ProductLog.type == ProductLogEntryType.REMOVE_BARCODE)
        .one()
    )
    assert log.product_id == product.id
    assert log.barcode == "0987654321"


def test_freed_code_can_be_used_by_another_product(sql_session: Session) -> None:
    product = _make_product(sql_session)
    add_barcode(sql_session, product, "0987654321")
    remove_barcode(sql_session, product, "0987654321")

    other = create_product(sql_session, "0987654321", "Pepsi", 20)

    sql_session.expire_all()

    assert {bc.code for bc in other.barcodes} == {"0987654321"}


@pytest.mark.parametrize(
    ("add_extra_barcode", "barcode", "error"),
    [
        pytest.param(False, "1234567890", "last barcode", id="last-code"),
        pytest.param(True, "1111111111", "not found", id="unknown"),
        pytest.param(True, "", "cannot be empty", id="empty"),
    ],
)
def test_invariants(
    sql_session: Session,
    add_extra_barcode: bool,
    barcode: str,
    error: str,
) -> None:
    product = _make_product(sql_session)
    if add_extra_barcode:
        add_barcode(sql_session, product, "0987654321")

    with pytest.raises(ValueError, match=error):
        remove_barcode(sql_session, product, barcode)

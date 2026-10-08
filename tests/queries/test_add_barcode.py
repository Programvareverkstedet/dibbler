import pytest
from sqlalchemy.orm import Session

from dibbler.models import Product, ProductLog
from dibbler.models.enums import ProductLogEntryType
from dibbler.queries import add_barcode, create_product


def _make_product(sql_session: Session) -> Product:
    return create_product(sql_session, "1234567890", "Cola", 15)


def test_appends_a_new_code(sql_session: Session) -> None:
    product = _make_product(sql_session)

    add_barcode(sql_session, product, "0987654321")

    sql_session.expire_all()

    assert {bc.code for bc in product.barcodes} == {"1234567890", "0987654321"}


def test_records_a_log_entry(sql_session: Session) -> None:
    product = _make_product(sql_session)

    add_barcode(sql_session, product, "0987654321")

    sql_session.expire_all()

    log = (
        sql_session.query(ProductLog)
        .filter(
            ProductLog.type == ProductLogEntryType.ADD_BARCODE,
            ProductLog.barcode == "0987654321",
        )
        .one()
    )
    assert log.product_id == product.id
    assert log.barcode == "0987654321"


@pytest.mark.parametrize(
    ("barcode", "error"),
    [
        pytest.param("", "Barcode cannot be empty", id="empty"),
        pytest.param("123abc", "digits only", id="non-digit"),
        pytest.param("1111111111", "already in use", id="used-by-other-product"),
        pytest.param("1234567890", "already in use", id="used-by-same-product"),
        pytest.param("1" * (Product.barcode_length + 1), "Barcode must be at most", id="too-long"),
    ],
)
def test_invariants(sql_session: Session, barcode: str, error: str) -> None:
    product = _make_product(sql_session)
    other = Product("1111111111", "Pepsi", 15)
    sql_session.add(other)
    sql_session.flush()

    with pytest.raises(ValueError, match=error):
        add_barcode(sql_session, product, barcode)

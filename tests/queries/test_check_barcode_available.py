import pytest
from sqlalchemy.orm import Session

from dibbler.queries import add_barcode, check_barcode_available, create_product


def _make_product(sql_session: Session) -> None:
    product = create_product(sql_session, "1234567890", "Cola", 15)
    add_barcode(sql_session, product, "1111111111")


@pytest.mark.parametrize(
    ("barcode", "error"),
    [
        pytest.param("0987654321", None, id="free"),
        pytest.param("1234567890", "already in use", id="taken-by-initial-barcode"),
        pytest.param("1111111111", "already in use", id="taken-by-added-barcode"),
    ],
)
def test_check_barcode_available(
    sql_session: Session,
    barcode: str,
    error: str | None,
) -> None:
    _make_product(sql_session)

    if error is None:
        check_barcode_available(sql_session, barcode)
    else:
        with pytest.raises(ValueError, match=error):
            check_barcode_available(sql_session, barcode)

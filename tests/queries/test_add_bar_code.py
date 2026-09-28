import pytest
from sqlalchemy.orm import Session

from dibbler.models import Product
from dibbler.queries import add_bar_code


def _make_product(sql_session: Session) -> Product:
    product = Product("1234567890", "Cola", 15, stock=10, hidden=False)
    sql_session.add(product)
    sql_session.flush()
    return product


def test_appends_a_new_code(sql_session: Session) -> None:
    product = _make_product(sql_session)

    add_bar_code(sql_session, product, "0987654321")

    sql_session.expire_all()

    assert {bc.code for bc in product.barcodes} == {"1234567890", "0987654321"}


def test_rejects_empty_code(sql_session: Session) -> None:
    product = _make_product(sql_session)

    with pytest.raises(ValueError, match="Barcode cannot be empty"):
        add_bar_code(sql_session, product, "")


def test_rejects_non_digit_code(sql_session: Session) -> None:
    product = _make_product(sql_session)

    with pytest.raises(ValueError, match="digits only"):
        add_bar_code(sql_session, product, "123abc")


def test_rejects_code_already_used_by_another_product(sql_session: Session) -> None:
    product = _make_product(sql_session)
    other = Product("1111111111", "Pepsi", 15)
    sql_session.add(other)
    sql_session.flush()

    with pytest.raises(ValueError, match="already in use"):
        add_bar_code(sql_session, product, "1111111111")


def test_rejects_code_already_on_the_same_product(sql_session: Session) -> None:
    product = _make_product(sql_session)

    with pytest.raises(ValueError, match="already in use"):
        add_bar_code(sql_session, product, "1234567890")

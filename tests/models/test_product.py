import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from dibbler.models import Product


def insert_test_data(sql_session: Session) -> Product:
    product = Product("1234567890123", "Test Product")
    sql_session.add(product)
    sql_session.commit()
    return product


def test_product_no_duplicate_barcodes(sql_session: Session) -> None:
    product = insert_test_data(sql_session)

    duplicate_product = Product(product.bar_code, "Hehe >:)")
    sql_session.add(duplicate_product)

    with pytest.raises(IntegrityError):
        sql_session.commit()


def test_product_no_duplicate_names(sql_session: Session) -> None:
    product = insert_test_data(sql_session)

    duplicate_product = Product("1918238911928", product.name)
    sql_session.add(duplicate_product)

    with pytest.raises(IntegrityError):
        sql_session.commit()

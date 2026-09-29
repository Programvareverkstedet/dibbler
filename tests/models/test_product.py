import pytest
from sqlalchemy.orm import Session

from dibbler.models import Product, ProductBarcode


def test_new_product_with_barcode_is_accepted(sql_session: Session) -> None:
    product = Product("1234567890123", "chips", price=10)
    sql_session.add(product)

    sql_session.flush()

    assert product.id is not None


def test_new_product_without_barcode_is_rejected(sql_session: Session) -> None:
    product = Product("1234567890123", "chips", price=10)
    product.barcodes = set()
    sql_session.add(product)

    with pytest.raises(ValueError, match="must have at least one barcode"):
        sql_session.flush()


def test_removing_the_last_barcode_is_rejected(sql_session: Session) -> None:
    product = Product("1234567890123", "chips", price=10)
    sql_session.add(product)
    sql_session.flush()

    product.barcodes.clear()

    with pytest.raises(ValueError, match="must have at least one barcode"):
        sql_session.flush()


def test_removing_one_of_several_barcodes_is_accepted(sql_session: Session) -> None:
    product = Product("1234567890123", "chips", price=10)
    product.barcodes.add(ProductBarcode(code="9876543210987"))
    sql_session.add(product)
    sql_session.flush()

    product.barcodes.remove(next(iter(product.barcodes)))
    sql_session.flush()

    assert len(product.barcodes) == 1


def test_deleting_a_product_is_accepted(sql_session: Session) -> None:
    product = Product("1234567890123", "chips", price=10)
    sql_session.add(product)
    sql_session.flush()

    sql_session.delete(product)
    sql_session.flush()

    assert sql_session.get(Product, product.id) is None

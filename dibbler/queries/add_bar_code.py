import re

from sqlalchemy.orm import Session

from dibbler.models import Product, ProductBarcode


def add_bar_code(sql_session: Session, product: Product, bar_code: str) -> Product:
    if not bar_code:
        raise ValueError("Barcode cannot be empty.")

    if not re.fullmatch(Product.bar_code_re, bar_code):
        raise ValueError("Barcode must consist of digits only.")

    if sql_session.query(ProductBarcode).filter(ProductBarcode.code == bar_code).first():
        raise ValueError("Barcode already in use.")

    product.barcodes.add(ProductBarcode(code=bar_code))

    sql_session.flush()

    return product

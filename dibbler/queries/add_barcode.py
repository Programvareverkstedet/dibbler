import re
from datetime import datetime

from sqlalchemy.orm import Session

from dibbler.models import Product, ProductBarcode, ProductLog
from dibbler.models.enums import ProductLogEntryType


def add_barcode(sql_session: Session, product: Product, barcode: str) -> Product:
    if not barcode:
        raise ValueError("Barcode cannot be empty.")

    if not re.fullmatch(Product.barcode_re, barcode):
        raise ValueError("Barcode must consist of digits only.")

    if len(barcode) > Product.barcode_length:
        raise ValueError(f"Barcode must be at most {Product.barcode_length} characters.")

    if sql_session.query(ProductBarcode).filter(ProductBarcode.code == barcode).first():
        raise ValueError("Barcode already in use.")

    product.barcodes.add(ProductBarcode(code=barcode))

    sql_session.add(
        ProductLog(
            type=ProductLogEntryType.ADD_BARCODE,
            time=datetime.now(),
            product_id=product.id,
            barcode=barcode,
        ),
    )

    sql_session.flush()

    return product

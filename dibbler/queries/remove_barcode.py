from datetime import datetime

from sqlalchemy.orm import Session

from dibbler.models import Product, ProductLog
from dibbler.models.enums import ProductLogEntryType


def remove_barcode(sql_session: Session, product: Product, barcode: str) -> Product:
    if not barcode:
        raise ValueError("Barcode cannot be empty.")

    matching = next((bc for bc in product.barcodes if bc.code == barcode), None)
    if matching is None:
        raise ValueError("Barcode not found on this product.")

    if len(product.barcodes) == 1:
        raise ValueError("Cannot remove a product's last barcode.")

    product.barcodes.remove(matching)

    sql_session.add(
        ProductLog(
            type=ProductLogEntryType.REMOVE_BARCODE,
            time=datetime.now(),
            product_id=product.id,
            barcode=barcode,
        ),
    )

    sql_session.flush()

    return product

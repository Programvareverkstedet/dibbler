from sqlalchemy.orm import Session

from dibbler.models import Product


def remove_bar_code(sql_session: Session, product: Product, bar_code: str) -> Product:
    if not bar_code:
        raise ValueError("Barcode cannot be empty.")

    matching = next((bc for bc in product.barcodes if bc.code == bar_code), None)
    if matching is None:
        raise ValueError("Barcode not found on this product.")

    if len(product.barcodes) == 1:
        raise ValueError("Cannot remove a product's last barcode.")

    product.barcodes.remove(matching)

    sql_session.flush()

    return product

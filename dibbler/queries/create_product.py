from sqlalchemy.orm import Session

from dibbler.models import Product


def create_product(
    sql_session: Session,
    name: str,
    barcode: str,
) -> Product:
    if not name:
        raise ValueError("Name cannot be empty.")

    if not barcode:
        raise ValueError("Barcode cannot be empty.")

    # TODO: check for duplicate names, barcodes

    # TODO: add more validation for barcode

    product = Product(barcode, name)
    sql_session.add(product)
    sql_session.commit()

    return product

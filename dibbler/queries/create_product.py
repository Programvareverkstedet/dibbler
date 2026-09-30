import re
from datetime import datetime

from sqlalchemy.orm import Session

from dibbler.models import Product, ProductBarcode, ProductLog
from dibbler.models.enums import ProductLogEntryType


def create_product(
    sql_session: Session,
    bar_code: str,
    name: str,
    price: int,
    stock: int = 0,
    hidden: bool = False,
) -> Product:
    if not bar_code:
        raise ValueError("Barcode cannot be empty.")

    if not re.fullmatch(Product.bar_code_re, bar_code):
        raise ValueError("Barcode must consist of digits only.")

    if len(bar_code) > Product.bar_code_length:
        raise ValueError(f"Barcode must be at most {Product.bar_code_length} characters.")

    if not name:
        raise ValueError("Name cannot be empty.")

    if len(name) > Product.name_length:
        raise ValueError(f"Name must be at most {Product.name_length} characters.")

    if price <= 0:
        raise ValueError("Price must be positive.")

    if sql_session.query(ProductBarcode).filter(ProductBarcode.code == bar_code).first():
        raise ValueError("Barcode already in use.")

    product = Product(bar_code, name, price, stock, hidden)
    sql_session.add(product)
    sql_session.flush()

    sql_session.add(
        ProductLog(
            type=ProductLogEntryType.CREATE,
            time=datetime.now(),
            product_id=product.id,
            name=product.name,
            price=product.price,
            hidden=product.hidden,
        ),
    )
    sql_session.add(
        ProductLog(
            type=ProductLogEntryType.ADD_BARCODE,
            time=datetime.now(),
            product_id=product.id,
            bar_code=bar_code,
        ),
    )
    sql_session.flush()

    return product

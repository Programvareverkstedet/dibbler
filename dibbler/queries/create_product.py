import re
from datetime import datetime

from sqlalchemy.orm import Session

from dibbler.models import Product, ProductBarcode, ProductLog, User
from dibbler.models.enums import ProductLogEntryType

from .adjust_stock import adjust_stock


def create_product(
    sql_session: Session,
    barcode: str,
    name: str,
    price: int,
    stock: int = 0,
    hidden: bool = False,
    user: User | None = None,
) -> Product:
    if not barcode:
        raise ValueError("Barcode cannot be empty.")

    if not re.fullmatch(Product.barcode_re, barcode):
        raise ValueError("Barcode must consist of digits only.")

    if len(barcode) > Product.barcode_length:
        raise ValueError(f"Barcode must be at most {Product.barcode_length} characters.")

    if not name:
        raise ValueError("Name cannot be empty.")

    if not re.fullmatch(Product.name_re, name):
        raise ValueError("Name has an invalid format.")

    if len(name) > Product.name_length:
        raise ValueError(f"Name must be at most {Product.name_length} characters.")

    if price <= 0:
        raise ValueError("Price must be positive.")

    if stock != 0 and user is None:
        raise ValueError("A user is required to set a non-zero initial stock.")

    if sql_session.query(ProductBarcode).filter(ProductBarcode.code == barcode).first():
        raise ValueError("Barcode already in use.")

    product = Product(barcode, name, price, 0, hidden)
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
            barcode=barcode,
        ),
    )
    sql_session.flush()

    if stock != 0:
        assert user is not None
        adjust_stock(sql_session, user, product, stock)

    return product

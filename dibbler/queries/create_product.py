import re

from sqlalchemy.orm import Session

from dibbler.models import Product


def create_product(
    sql_session: Session,
    bar_code: str,
    name: str,
    price: int,
    stock: int = 0,
    hidden: bool = False,
) -> Product:
    if not bar_code:
        raise ValueError("Bar code cannot be empty.")

    if not re.fullmatch(Product.bar_code_re, bar_code):
        raise ValueError("Bar code must consist of digits only.")

    if not name:
        raise ValueError("Name cannot be empty.")

    if price <= 0:
        raise ValueError("Price must be positive.")

    product = Product(bar_code, name, price, stock, hidden)
    sql_session.add(product)
    sql_session.flush()

    return product

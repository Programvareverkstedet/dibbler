import re
from typing import Any

from sqlalchemy.orm import Session

from dibbler.models import Product

UNSET: Any = object()


def edit_product(
    sql_session: Session,
    product: Product,
    name: str = UNSET,
    price: int = UNSET,
    bar_code: str = UNSET,
    hidden: bool = UNSET,
) -> Product:
    if name is UNSET and price is UNSET and bar_code is UNSET and hidden is UNSET:
        raise ValueError("Nothing to edit.")

    if name is not UNSET and not name:
        raise ValueError("Name cannot be empty.")

    if price is not UNSET and price <= 0:
        raise ValueError("Price must be positive.")

    if bar_code is not UNSET:
        if not bar_code:
            raise ValueError("Bar code cannot be empty.")
        if not re.fullmatch(Product.bar_code_re, bar_code):
            raise ValueError("Bar code must consist of digits only.")

    if name is not UNSET:
        product.name = name

    if price is not UNSET:
        product.price = price

    if bar_code is not UNSET:
        product.bar_code = bar_code

    if hidden is not UNSET:
        product.hidden = hidden

    sql_session.flush()

    return product

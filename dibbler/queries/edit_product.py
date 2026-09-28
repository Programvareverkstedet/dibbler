from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from dibbler.models import Product, ProductLog
from dibbler.models.enums import ProductLogEntryType

UNSET: Any = object()


def edit_product(
    sql_session: Session,
    product: Product,
    name: str = UNSET,
    price: int = UNSET,
    hidden: bool = UNSET,
) -> Product:
    if name is not UNSET and not name:
        raise ValueError("Name cannot be empty.")

    if price is not UNSET and price <= 0:
        raise ValueError("Price must be positive.")

    changed = (
        (name is not UNSET and name != product.name)
        or (price is not UNSET and price != product.price)
        or (hidden is not UNSET and hidden != product.hidden)
    )
    if not changed:
        raise ValueError("Nothing to edit.")

    if name is not UNSET:
        product.name = name

    if price is not UNSET:
        product.price = price

    if hidden is not UNSET:
        product.hidden = hidden

    sql_session.add(
        ProductLog(
            type=ProductLogEntryType.EDIT,
            time=datetime.now(),
            product_id=product.id,
            name=name if name is not UNSET else None,
            price=price if price is not UNSET else None,
            hidden=hidden if hidden is not UNSET else None,
        ),
    )

    sql_session.flush()

    return product

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from dibbler.models import Product


def list_products_nonzero_stock_query() -> Select[tuple[Product]]:
    return (
        select(Product)
        .where(Product.hidden.is_(False), Product.stock != 0)
        .order_by(Product.name, Product.id)
    )


def list_products_nonzero_stock(sql_session: Session) -> list[Product]:
    """Non-hidden products with a non-zero stock level."""
    return list(sql_session.scalars(list_products_nonzero_stock_query()))

from collections.abc import Iterator

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from dibbler.models import Product

from .._helpers import DEFAULT_STREAMING_ITER_CHUNK_SIZE, iter_in_chunks


def products_nonzero_stock_query(include_hidden: bool = False) -> Select[tuple[Product]]:
    query = select(Product).where(Product.stock != 0).order_by(Product.name, Product.id)

    if not include_hidden:
        query = query.where(Product.hidden.is_(False))

    return query


def products_nonzero_stock_list(
    sql_session: Session,
    include_hidden: bool = False,
) -> list[Product]:
    """Products with a non-zero stock level, optionally including hidden ones."""
    return list(sql_session.scalars(products_nonzero_stock_query(include_hidden)))


def products_nonzero_stock_stream(
    sql_session: Session,
    include_hidden: bool = False,
    chunk_size: int = DEFAULT_STREAMING_ITER_CHUNK_SIZE,
) -> Iterator[Product]:
    """
    Streaming variant of `products_nonzero_stock_list`, which fetches `chunk_size` products
    at a time.
    """
    return iter_in_chunks(sql_session, products_nonzero_stock_query(include_hidden), chunk_size)

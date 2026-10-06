from collections.abc import Iterator
from datetime import datetime
from typing import NamedTuple

from sqlalchemy import Integer, Select, func, select
from sqlalchemy.orm import Session

from dibbler.models import Product, TransactionLog, TransactionLogProduct
from dibbler.models.enums import TransactionLogEntryType

from .._helpers import (
    DEFAULT_STREAMING_ITER_CHUNK_SIZE,
    iter_rows_in_chunks,
    time_window_conditions,
)


class ProductSales(NamedTuple):
    product: Product
    """Product that was sold."""

    sold_amount: int
    """Total number of units sold."""

    sold_credit: int
    """Total credit earned from the units sold, penalties not included."""


def products_top_selling_query(
    after_time: datetime | None = None,
    before_time: datetime | None = None,
    rank_by_credit: bool = False,
) -> Select[tuple[Product, int, int]]:
    sold_amount = func.sum(-TransactionLogProduct.amount, type_=Integer)
    sold_credit = func.sum(
        -TransactionLogProduct.amount * TransactionLogProduct.price_at_time,
        type_=Integer,
    )

    return (
        select(Product, sold_amount, sold_credit)
        .join(TransactionLogProduct, TransactionLogProduct.product_id == Product.id)
        .join(TransactionLogProduct.transaction)
        .where(
            TransactionLog.type == TransactionLogEntryType.BUY_PRODUCT,
            *time_window_conditions(TransactionLog.time, after_time, before_time),
        )
        .group_by(Product.id)
        .order_by((sold_credit if rank_by_credit else sold_amount).desc(), Product.id)
    )


def products_top_selling_list(
    sql_session: Session,
    limit: int | None = 20,
    after_time: datetime | None = None,
    before_time: datetime | None = None,
    rank_by_credit: bool = False,
) -> list[ProductSales]:
    """Top products ranked by number of units sold."""

    if limit is not None and limit <= 0:
        raise ValueError("Limit must be positive.")

    query = products_top_selling_query(after_time, before_time, rank_by_credit)
    return [ProductSales(*row) for row in sql_session.execute(query.limit(limit))]


def products_top_selling_stream(
    sql_session: Session,
    after_time: datetime | None = None,
    before_time: datetime | None = None,
    rank_by_credit: bool = False,
    chunk_size: int = DEFAULT_STREAMING_ITER_CHUNK_SIZE,
) -> Iterator[ProductSales]:
    """
    Streaming variant of `products_top_selling_list`, which fetches `chunk_size` products
    at a time.
    """
    query = products_top_selling_query(after_time, before_time, rank_by_credit)
    return (ProductSales(*row) for row in iter_rows_in_chunks(sql_session, query, chunk_size))

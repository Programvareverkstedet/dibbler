from collections.abc import Iterator
from datetime import datetime
from typing import NamedTuple

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session, selectinload

from dibbler.models import Product, TransactionLog, TransactionLogProduct
from dibbler.models.enums import TransactionLogEntryType

from ._helpers import DEFAULT_STREAMING_ITER_CHUNK_SIZE, iter_rows_in_chunks, sum_where


class ProductListInfo(NamedTuple):
    product: Product
    times_bought: int
    times_added: int
    last_activity: datetime | None


def product_list_info_query() -> Select[tuple[Product, int, int, datetime | None]]:
    totals = (
        select(
            TransactionLogProduct.product_id,
            sum_where(
                TransactionLog.type == TransactionLogEntryType.BUY_PRODUCT,
                -TransactionLogProduct.amount,
            ).label("bought"),
            sum_where(
                TransactionLog.type == TransactionLogEntryType.ADD_PRODUCT,
                TransactionLogProduct.amount,
            ).label("added"),
            func.max(TransactionLog.time).label("last_activity"),
        )
        .join(TransactionLogProduct.transaction)
        .group_by(TransactionLogProduct.product_id)
        .subquery()
    )

    return (
        select(
            Product,
            func.coalesce(totals.c.bought, 0),
            func.coalesce(totals.c.added, 0),
            totals.c.last_activity,
        )
        .outerjoin(totals, totals.c.product_id == Product.id)
        .where(Product.hidden.is_(False))
        .options(selectinload(Product.barcodes))
        .order_by(Product.stock.desc(), Product.id)
    )


def product_list_info(sql_session: Session) -> list[ProductListInfo]:
    """
    Retrieve all non-hidden products with their bought/added counts and last activity.

    Sorted by stock, highest first.
    """
    return [ProductListInfo(*row) for row in sql_session.execute(product_list_info_query())]


def product_list_info_stream(
    sql_session: Session,
    chunk_size: int = DEFAULT_STREAMING_ITER_CHUNK_SIZE,
) -> Iterator[ProductListInfo]:
    """Streaming variant of `product_list_info`, which fetches `chunk_size` products at a time."""
    query = product_list_info_query()
    return (ProductListInfo(*row) for row in iter_rows_in_chunks(sql_session, query, chunk_size))

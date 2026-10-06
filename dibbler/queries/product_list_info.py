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


def product_list_info_query(
    include_hidden: bool = False,
    include_zero_stock: bool = True,
) -> Select[tuple[Product, int, int, datetime | None]]:
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

    query = (
        select(
            Product,
            func.coalesce(totals.c.bought, 0),
            func.coalesce(totals.c.added, 0),
            totals.c.last_activity,
        )
        .outerjoin(totals, totals.c.product_id == Product.id)
        .options(selectinload(Product.barcodes))
        .order_by(Product.stock.desc(), Product.id)
    )

    if not include_hidden:
        query = query.where(Product.hidden.is_(False))

    if not include_zero_stock:
        query = query.where(Product.stock != 0)

    return query


def product_list_info(
    sql_session: Session,
    include_hidden: bool = False,
    include_zero_stock: bool = True,
) -> list[ProductListInfo]:
    """
    Retrieve products with their bought/added counts and last activity.

    Sorted by stock, highest first.
    """
    query = product_list_info_query(include_hidden, include_zero_stock)
    return [ProductListInfo(*row) for row in sql_session.execute(query)]


def product_list_info_stream(
    sql_session: Session,
    include_hidden: bool = False,
    include_zero_stock: bool = True,
    chunk_size: int = DEFAULT_STREAMING_ITER_CHUNK_SIZE,
) -> Iterator[ProductListInfo]:
    """Streaming variant of `product_list_info`, which fetches `chunk_size` products at a time."""
    query = product_list_info_query(include_hidden, include_zero_stock)
    return (ProductListInfo(*row) for row in iter_rows_in_chunks(sql_session, query, chunk_size))

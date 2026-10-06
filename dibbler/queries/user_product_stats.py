from collections.abc import Iterator
from datetime import datetime
from typing import NamedTuple

from sqlalchemy import Integer, Select, case, func, select
from sqlalchemy.orm import Session

from dibbler.models import Product, TransactionLog, TransactionLogProduct, User
from dibbler.models.enums import TransactionLogEntryType

from ._helpers import DEFAULT_STREAMING_ITER_CHUNK_SIZE, iter_rows_in_chunks, time_window_conditions


class UserProductStats(NamedTuple):
    product: Product
    bought: int
    added: int


def user_product_stats_query(
    user: User,
    after_time: datetime | None = None,
    before_time: datetime | None = None,
    limit: int | None = None,
) -> Select[tuple[Product, int, int]]:
    conditions = time_window_conditions(TransactionLog.time, after_time, before_time)

    if limit is not None and limit <= 0:
        raise ValueError("Limit must be positive.")

    bought = func.sum(
        case(
            (
                TransactionLog.type == TransactionLogEntryType.BUY_PRODUCT,
                -TransactionLogProduct.amount,
            ),
            else_=0,
        ),
        type_=Integer,
    )
    added = func.sum(
        case(
            (
                TransactionLog.type == TransactionLogEntryType.ADD_PRODUCT,
                TransactionLogProduct.amount,
            ),
            else_=0,
        ),
        type_=Integer,
    )

    stats = (
        select(Product.id.label("product_id"), bought.label("bought"), added.label("added"))
        .select_from(TransactionLog)
        .where(
            TransactionLog.type.in_(
                [TransactionLogEntryType.BUY_PRODUCT, TransactionLogEntryType.ADD_PRODUCT],
            ),
            TransactionLog.users.any(user=user),
            *conditions,
        )
        .join(TransactionLog.products)
        .join(TransactionLogProduct.product)
        .group_by(Product.id)
        .order_by(bought.desc(), added.desc(), Product.name, Product.id)
        .limit(limit)
        .subquery()
    )

    return (
        select(Product, stats.c.bought, stats.c.added)
        .join(stats, stats.c.product_id == Product.id)
        .order_by(stats.c.bought.desc(), stats.c.added.desc(), Product.name, Product.id)
    )


def user_product_stats(
    sql_session: Session,
    user: User,
    after_time: datetime | None = None,
    before_time: datetime | None = None,
    limit: int | None = None,
) -> list[UserProductStats]:
    """
    Retrieve how many of each product a user has bought and added.

    - Sorted by the amount bought, then the amount added, both descending.
    - Purchases or restocks shared between several users count the full amount for each of them.
    - `after_time` is inclusive and `before_time` is exclusive.
    - If `limit` is given, only the `limit` first products are returned.
    """
    query = user_product_stats_query(
        user=user,
        after_time=after_time,
        before_time=before_time,
        limit=limit,
    )
    return [UserProductStats(*row) for row in sql_session.execute(query)]


def user_product_stats_stream(
    sql_session: Session,
    user: User,
    after_time: datetime | None = None,
    before_time: datetime | None = None,
    limit: int | None = None,
    chunk_size: int = DEFAULT_STREAMING_ITER_CHUNK_SIZE,
) -> Iterator[UserProductStats]:
    """
    Streaming variant of `user_product_stats`, which fetches `chunk_size` products at a time.
    """
    query = user_product_stats_query(
        user=user,
        after_time=after_time,
        before_time=before_time,
        limit=limit,
    )
    return (UserProductStats(*row) for row in iter_rows_in_chunks(sql_session, query, chunk_size))

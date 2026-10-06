from collections.abc import Iterator
from datetime import datetime

from sqlalchemy import Select, select
from sqlalchemy.orm import Session, selectinload

from dibbler.models import Product, TransactionLog, TransactionLogProduct, TransactionLogUser, User
from dibbler.models.enums import TransactionLogEntryType

from ._helpers import (
    DEFAULT_STREAMING_ITER_CHUNK_SIZE,
    iter_in_keyset_chunks,
    time_window_conditions,
)


def transaction_log_query(
    user: User | None = None,
    product: Product | None = None,
    after_time: datetime | None = None,
    before_time: datetime | None = None,
    entry_type: list[TransactionLogEntryType] | None = None,
    negate_entry_type_filter: bool = False,
    limit: int | None = None,
    newest_first: bool = False,
) -> Select[tuple[TransactionLog]]:
    if user is not None and product is not None:
        raise ValueError("Cannot filter by both user and product.")

    time_conditions = time_window_conditions(TransactionLog.time, after_time, before_time)

    if limit is not None and limit <= 0:
        raise ValueError("Limit must be positive.")

    optional_conditions = [
        user is not None and TransactionLog.users.any(user=user),
        product is not None and TransactionLog.products.any(product=product),
        entry_type is not None
        and (
            TransactionLog.type.not_in(entry_type)
            if negate_entry_type_filter
            else TransactionLog.type.in_(entry_type)
        ),
    ]
    conditions = [
        *(condition for condition in optional_conditions if not isinstance(condition, bool)),
        *time_conditions,
    ]

    if limit is not None:
        conditions.append(
            TransactionLog.id.in_(
                select(TransactionLog.id)
                .where(*conditions)
                .order_by(TransactionLog.time.desc(), TransactionLog.id.desc())
                .limit(limit),
            ),
        )

    ordering = (
        (TransactionLog.time.desc(), TransactionLog.id.desc())
        if newest_first
        else (TransactionLog.time.asc(), TransactionLog.id.asc())
    )

    return (
        select(TransactionLog)
        .where(*conditions)
        .options(
            selectinload(TransactionLog.users).selectinload(TransactionLogUser.user),
            selectinload(TransactionLog.products).selectinload(TransactionLogProduct.product),
        )
        .order_by(*ordering)
    )


def transaction_log(
    sql_session: Session,
    user: User | None = None,
    product: Product | None = None,
    after_time: datetime | None = None,
    before_time: datetime | None = None,
    entry_type: list[TransactionLogEntryType] | None = None,
    negate_entry_type_filter: bool = False,
    limit: int | None = None,
    newest_first: bool = False,
) -> list[TransactionLog]:
    """
    Retrieve the transaction log in chronological order, optionally filtered.

    - The order is reversed if `newest_first` is set.
    - Only one of `user` or `product` may be specified.
    - `after_time` is inclusive and `before_time` is exclusive.
    - If `limit` is given, the `limit` most recent matching entries are returned.
    """
    query = transaction_log_query(
        user=user,
        product=product,
        after_time=after_time,
        before_time=before_time,
        entry_type=entry_type,
        negate_entry_type_filter=negate_entry_type_filter,
        limit=limit,
        newest_first=newest_first,
    )
    return list(sql_session.scalars(query))


def transaction_log_stream(
    sql_session: Session,
    user: User | None = None,
    product: Product | None = None,
    after_time: datetime | None = None,
    before_time: datetime | None = None,
    entry_type: list[TransactionLogEntryType] | None = None,
    negate_entry_type_filter: bool = False,
    limit: int | None = None,
    newest_first: bool = False,
    chunk_size: int = DEFAULT_STREAMING_ITER_CHUNK_SIZE,
) -> Iterator[TransactionLog]:
    """
    Streaming variant of `transaction_log`, which fetches `chunk_size` entries at a time.
    """
    query = transaction_log_query(
        user=user,
        product=product,
        after_time=after_time,
        before_time=before_time,
        entry_type=entry_type,
        negate_entry_type_filter=negate_entry_type_filter,
        limit=limit,
        newest_first=newest_first,
    )
    return iter_in_keyset_chunks(
        sql_session,
        query,
        keys=(TransactionLog.time, TransactionLog.id),
        descending=newest_first,
        chunk_size=chunk_size,
    )

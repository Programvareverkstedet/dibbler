from datetime import datetime

from sqlalchemy import Select, select
from sqlalchemy.orm import Session, selectinload

from dibbler.models import Product, TransactionLog, TransactionLogProduct, TransactionLogUser, User
from dibbler.models.enums import TransactionLogEntryType


def transaction_log_query(
    user: User | None = None,
    product: Product | None = None,
    after_time: datetime | None = None,
    before_time: datetime | None = None,
    entry_type: list[TransactionLogEntryType] | None = None,
    negate_entry_type_filter: bool = False,
    limit: int | None = None,
) -> Select[tuple[TransactionLog]]:
    """
    Query variant of `transaction_log`, useful for use with the `iter_in_chunks` helper.
    """

    if user is not None and product is not None:
        raise ValueError("Cannot filter by both user and product.")

    if after_time is not None and before_time is not None and after_time > before_time:
        raise ValueError("after_time cannot be after before_time.")

    if limit is not None and limit <= 0:
        raise ValueError("Limit must be positive.")

    optional_conditions = [
        user is not None and TransactionLog.users.any(user=user),
        product is not None and TransactionLog.products.any(product=product),
        after_time is not None and TransactionLog.time >= after_time,
        before_time is not None and TransactionLog.time < before_time,
        entry_type is not None
        and (
            TransactionLog.type.not_in(entry_type)
            if negate_entry_type_filter
            else TransactionLog.type.in_(entry_type)
        ),
    ]
    conditions = [condition for condition in optional_conditions if not isinstance(condition, bool)]

    if limit is not None:
        conditions.append(
            TransactionLog.id.in_(
                select(TransactionLog.id)
                .where(*conditions)
                .order_by(TransactionLog.time.desc(), TransactionLog.id.desc())
                .limit(limit),
            ),
        )

    return (
        select(TransactionLog)
        .where(*conditions)
        .options(
            selectinload(TransactionLog.users).selectinload(TransactionLogUser.user),
            selectinload(TransactionLog.products).selectinload(TransactionLogProduct.product),
        )
        .order_by(TransactionLog.time.asc(), TransactionLog.id.asc())
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
) -> list[TransactionLog]:
    """
    Retrieve the transaction log in chronological order, optionally filtered.

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
    )
    return list(sql_session.scalars(query))

from sqlalchemy import select
from sqlalchemy.orm import Session

from dibbler.models import (
    Product,
    Transaction,
    TransactionType,
    User,
)


# TODO: should this include full joint transactions that involve a user?
# TODO: should this involve throw-away transactions that affects a user?
def transaction_log(
    sql_session: Session,
    user: User | None = None,
    product: Product | None = None,
    exclusive_after: bool = False,
    after_time=None,
    after_transaction_id: int | None = None,
    exclusive_before: bool = False,
    before_time=None,
    before_transaction_id: int | None = None,
    transaction_type: list[TransactionType] | None = None,
    negate_transaction_type_filter: bool = False,
    limit: int | None = None,
) -> list[Transaction]:
    """
    Retrieve the transaction log, optionally filtered.

    Only one of `user` or `product` may be specified.
    Only one of `after_time` or `after_transaction_id` may be specified.
    Only one of `before_time` or `before_transaction_id` may be specified.

    The before and after filters are inclusive by default.
    """

    if not (user is None or product is None):
        raise ValueError("Cannot filter by both user and product.")

    if not (after_time is None or after_transaction_id is None):
        raise ValueError("Cannot filter by both from_time and from_transaction_id.")

    query = select(Transaction)
    if user is not None:
        query = query.where(Transaction.user_id == user.id)
    if product is not None:
        query = query.where(Transaction.product_id == product.id)

    if after_time is not None:
        if exclusive_after:
            query = query.where(Transaction.time > after_time)
        else:
            query = query.where(Transaction.time >= after_time)
    if after_transaction_id is not None:
        if exclusive_after:
            query = query.where(Transaction.id > after_transaction_id)
        else:
            query = query.where(Transaction.id >= after_transaction_id)

    if before_time is not None:
        if exclusive_before:
            query = query.where(Transaction.time < before_time)
        else:
            query = query.where(Transaction.time <= before_time)
    if before_transaction_id is not None:
        if exclusive_before:
            query = query.where(Transaction.id < before_transaction_id)
        else:
            query = query.where(Transaction.id <= before_transaction_id)

    if transaction_type is not None:
        if negate_transaction_type_filter:
            query = query.where(~Transaction.type_.in_(transaction_type))
        else:
            query = query.where(Transaction.type_.in_(transaction_type))

    if limit is not None:
        query = query.limit(limit)

    query = query.order_by(Transaction.time.asc(), Transaction.id.asc())
    result = sql_session.scalars(query).all()

    return list(result)

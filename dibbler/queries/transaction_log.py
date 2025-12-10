from datetime import datetime

from sqlalchemy import BindParameter, select
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
    until_time: BindParameter[datetime] | datetime | None = None,
    until_transaction: Transaction | None = None,
    until_inclusive: bool = True,
    after_time: BindParameter[datetime] | datetime | None = None,
    after_transaction: Transaction | None = None,
    after_inclusive: bool = True,
    transaction_type: list[TransactionType] | None = None,
    negate_transaction_type_filter: bool = False,
    limit: int | None = None,
) -> list[Transaction]:
    """
    Retrieve the transaction log, optionally filtered.

    Only one of `user` or `product` may be specified.
    Only one of `until_time` or `until_transaction_id` may be specified.
    Only one of `after_time` or `after_transaction_id` may be specified.

    The after and after filters are inclusive by default.
    """

    if not (user is None or product is None):
        raise ValueError("Cannot filter by both user and product.")

    if isinstance(user, User):
        if user.id is None:
            raise ValueError("User must be persisted in the database.")
        user_id = BindParameter("user_id", value=user.id)
    else:
        user_id = None

    if isinstance(product, Product):
        if product.id is None:
            raise ValueError("Product must be persisted in the database.")
        product_id = BindParameter("product_id", value=product.id)
    else:
        product_id = None

    if not (until_time is None or until_transaction is None):
        raise ValueError("Cannot filter by both after_time and after_transaction_id.")

    if isinstance(until_time, datetime):
        until_time = BindParameter("until_time", value=until_time)

    if isinstance(until_transaction, Transaction):
        if until_transaction.id is None:
            raise ValueError("until_transaction must be persisted in the database.")
        until_transaction_id = BindParameter("until_transaction_id", value=until_transaction.id)
    else:
        until_transaction_id = None

    if not (after_time is None or after_transaction is None):
        raise ValueError("Cannot filter by both after_time and after_transaction_id.")

    if isinstance(after_time, datetime):
        after_time = BindParameter("after_time", value=after_time)

    if isinstance(after_transaction, Transaction):
        if after_transaction.id is None:
            raise ValueError("after_transaction must be persisted in the database.")
        after_transaction_id = BindParameter("after_transaction_id", value=after_transaction.id)
    else:
        after_transaction_id = None

    if after_time is not None and until_time is not None:
        assert isinstance(after_time.value, datetime)
        assert isinstance(until_time.value, datetime)

        if after_time.value > until_time.value:
            raise ValueError("after_time cannot be after until_time.")

    if after_transaction is not None and until_transaction is not None:
        assert after_transaction.time is not None
        assert until_transaction.time is not None

        if after_transaction.time > until_transaction.time:
            raise ValueError("after_transaction cannot be after until_transaction.")

    if limit is not None and limit <= 0:
        raise ValueError("Limit must be positive.")

    query = select(Transaction)
    if user is not None:
        query = query.where(Transaction.user_id == user_id)
    if product is not None:
        query = query.where(Transaction.product_id == product_id)

    match (until_time, until_transaction_id, until_inclusive):
        case (BindParameter(), None, True):
            query = query.where(Transaction.time <= until_time)
        case (BindParameter(), None, False):
            query = query.where(Transaction.time < until_time)
        case (None, BindParameter(), True):
            query = query.where(Transaction.id <= until_transaction_id)
        case (None, BindParameter(), False):
            query = query.where(Transaction.id < until_transaction_id)
        case _:
            pass

    match (after_time, after_transaction_id, after_inclusive):
        case (BindParameter(), None, True):
            query = query.where(Transaction.time >= after_time)
        case (BindParameter(), None, False):
            query = query.where(Transaction.time > after_time)
        case (None, BindParameter(), True):
            query = query.where(Transaction.id >= after_transaction_id)
        case (None, BindParameter(), False):
            query = query.where(Transaction.id > after_transaction_id)
        case _:
            pass

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

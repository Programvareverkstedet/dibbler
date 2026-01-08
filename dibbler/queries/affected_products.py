from datetime import datetime

from sqlalchemy import BindParameter, select
from sqlalchemy.orm import Session

from dibbler.models import Product, Transaction, TransactionType
from dibbler.queries.query_helpers import after_filter, until_filter


def affected_products(
    sql_session: Session,
    until_time: BindParameter[datetime] | datetime | None = None,
    until_transaction: BindParameter[Transaction] | Transaction | None = None,
    until_inclusive: bool = True,
    after_time: BindParameter[datetime] | datetime | None = None,
    after_transaction: Transaction | None = None,
    after_inclusive: bool = True,
) -> set[Product]:
    """
    Get all products where attributes were affected over a given interval.
    """

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

    result = sql_session.scalars(
        select(Product)
        .distinct()
        .join(Transaction, Product.id == Transaction.product_id)
        .where(
            Transaction.type_.in_(
                [
                    TransactionType.ADD_PRODUCT.as_literal_column(),
                    TransactionType.ADJUST_STOCK.as_literal_column(),
                    TransactionType.BUY_PRODUCT.as_literal_column(),
                    TransactionType.JOINT.as_literal_column(),
                    TransactionType.THROW_PRODUCT.as_literal_column(),
                ],
            ),
            until_filter(
                until_time=until_time,
                until_transaction_id=until_transaction_id,
                until_inclusive=until_inclusive,
            ),
            after_filter(
                after_time=after_time,
                after_transaction_id=after_transaction_id,
                after_inclusive=after_inclusive,
            ),
        )
        .order_by(Transaction.time.desc()),
    ).all()

    return set(result)

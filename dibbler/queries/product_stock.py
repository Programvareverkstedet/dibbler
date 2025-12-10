from datetime import datetime
from typing import Tuple

from sqlalchemy import (
    BindParameter,
    Select,
    bindparam,
    case,
    func,
    select,
)
from sqlalchemy.orm import Session

from dibbler.models import (
    Product,
    Transaction,
    TransactionType,
)
from dibbler.queries.query_helpers import until_filter


def _product_stock_query(
    product_id: BindParameter[int] | int,
    use_cache: bool = True,
    until_time: BindParameter[datetime] | datetime | None = None,
    until_transaction: Transaction | None = None,
    until_inclusive: bool = True,
) -> Select[tuple[int]]:
    """
    The inner query for calculating the product stock.
    """

    if use_cache:
        print("WARNING: Using cache for product stock query is not implemented yet.")

    if isinstance(product_id, int):
        product_id = BindParameter("product_id", value=product_id)

    if not (until_time is None or until_transaction is None):
        raise ValueError("Cannot filter by both until_time and until_transaction.")

    if isinstance(until_time, datetime):
        until_time = BindParameter("until_time", value=until_time)

    if isinstance(until_transaction, Transaction):
        if until_transaction.id is None:
            raise ValueError("until_transaction must be persisted in the database.")
        until_transaction_id = bindparam("until_transaction_id", value=until_transaction.id)
    else:
        until_transaction_id = None

    query = select(
        func.sum(
            case(
                (
                    Transaction.type_ == TransactionType.ADD_PRODUCT.as_literal_column(),
                    Transaction.product_count,
                ),
                (
                    Transaction.type_ == TransactionType.ADJUST_STOCK.as_literal_column(),
                    Transaction.product_count,
                ),
                (
                    Transaction.type_ == TransactionType.BUY_PRODUCT.as_literal_column(),
                    -Transaction.product_count,
                ),
                (
                    Transaction.type_ == TransactionType.JOINT.as_literal_column(),
                    -Transaction.product_count,
                ),
                (
                    Transaction.type_ == TransactionType.THROW_PRODUCT.as_literal_column(),
                    -Transaction.product_count,
                ),
                else_=0,
            ),
        ).label("stock"),
    ).where(
        Transaction.type_.in_(
            [
                TransactionType.ADD_PRODUCT.as_literal_column(),
                TransactionType.ADJUST_STOCK.as_literal_column(),
                TransactionType.BUY_PRODUCT.as_literal_column(),
                TransactionType.JOINT.as_literal_column(),
                TransactionType.THROW_PRODUCT.as_literal_column(),
            ],
        ),
        Transaction.product_id == product_id,
        until_filter(
            until_time=until_time,
            until_transaction_id=until_transaction_id,
            until_inclusive=until_inclusive,
        ),
    )

    return query


def product_stock(
    sql_session: Session,
    product: Product,
    use_cache: bool = True,
    until_time: BindParameter[datetime] | datetime | None = None,
    until_transaction: Transaction | None = None,
    until_inclusive: bool = True,
) -> int:
    """
    Returns the number of products in stock.

    If 'until' is given, only transactions up to that time are considered.
    """

    if product.id is None:
        raise ValueError("Product must be persisted in the database.")

    query = _product_stock_query(
        product_id=product.id,
        use_cache=use_cache,
        until_time=until_time,
        until_transaction=until_transaction,
        until_inclusive=until_inclusive,
    )

    result = sql_session.scalars(query).one_or_none()

    return result or 0

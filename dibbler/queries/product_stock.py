from datetime import datetime

from sqlalchemy import (
    BindParameter,
    Select,
    case,
    func,
    select,
)
from sqlalchemy.orm import Session

from dibbler.lib.query_helpers import CONST_TRUE
from dibbler.models import (
    Product,
    Transaction,
    TransactionType,
)


def _product_stock_query(
    product_id: BindParameter[int] | int,
    use_cache: bool = True,
    until: BindParameter[datetime] | datetime | None = None,
) -> Select:
    """
    The inner query for calculating the product stock.
    """

    if use_cache:
        print("WARNING: Using cache for product stock query is not implemented yet.")

    if isinstance(product_id, int):
        product_id = BindParameter("product_id", value=product_id)

    if isinstance(until, datetime):
        until = BindParameter("until", value=until)

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
            )
        )
    ).where(
        Transaction.type_.in_(
            [
                TransactionType.ADD_PRODUCT.as_literal_column(),
                TransactionType.ADJUST_STOCK.as_literal_column(),
                TransactionType.BUY_PRODUCT.as_literal_column(),
                TransactionType.JOINT.as_literal_column(),
                TransactionType.THROW_PRODUCT.as_literal_column(),
            ]
        ),
        Transaction.product_id == product_id,
        Transaction.time <= until if until is not None else CONST_TRUE,
    )

    return query


# TODO: add until transaction parameter

def product_stock(
    sql_session: Session,
    product: Product,
    use_cache: bool = True,
    until: datetime | None = None,
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
        until=until,
    )

    result = sql_session.scalars(query).one_or_none()

    return result or 0

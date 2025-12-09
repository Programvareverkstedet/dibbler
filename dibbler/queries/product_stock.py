from datetime import datetime

from sqlalchemy import case, func, literal, select
from sqlalchemy.orm import Session

from dibbler.models import (
    Product,
    Transaction,
    TransactionType,
)


def _product_stock_query(
    product_id: int,
    use_cache: bool = True,
    until: datetime | None = None,
):
    """
    The inner query for calculating the product stock.
    """

    if use_cache:
        print("WARNING: Using cache for product stock query is not implemented yet.")

    query = select(
        func.sum(
            case(
                (
                    Transaction.type_ == TransactionType.ADD_PRODUCT,
                    Transaction.product_count,
                ),
                (
                    Transaction.type_ == TransactionType.ADJUST_STOCK,
                    Transaction.product_count,
                ),
                (
                    Transaction.type_ == TransactionType.BUY_PRODUCT,
                    -Transaction.product_count,
                ),
                (
                    Transaction.type_ == TransactionType.JOINT,
                    -Transaction.product_count,
                ),
                (
                    Transaction.type_ == TransactionType.THROW_PRODUCT,
                    -Transaction.product_count,
                ),
                else_=0,
            )
        )
    ).where(
        Transaction.type_.in_(
            [
                TransactionType.ADD_PRODUCT,
                TransactionType.ADJUST_STOCK,
                TransactionType.BUY_PRODUCT,
                TransactionType.JOINT,
                TransactionType.THROW_PRODUCT,
            ]
        ),
        Transaction.product_id == product_id,
        Transaction.time <= until if until is not None else literal(True),
    )

    return query


def product_stock(
    sql_session: Session,
    product: Product,
    use_cache: bool = True,
    until: datetime | None = None,
) -> int:
    """
    Returns the number of products in stock.
    """

    query = _product_stock_query(
        product_id=product.id,
        use_cache=use_cache,
        until=until,
    )

    result = sql_session.scalars(query).one_or_none()

    return result or 0

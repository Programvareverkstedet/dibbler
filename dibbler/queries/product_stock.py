from datetime import datetime

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from dibbler.models import (
    Product,
    Transaction,
    TransactionType,
)


def product_stock(
    sql_session: Session,
    product: Product,
    use_cache: bool = True,
    until: datetime | None = None,
) -> int:
    """
    Returns the number of products in stock.
    """

    if use_cache:
        print("WARNING: Using cache for product stock query is not implemented yet.")

    result = sql_session.scalars(
        select(
            func.sum(
                case(
                    (
                        Transaction.type_ == TransactionType.ADD_PRODUCT,
                        Transaction.product_count,
                    ),
                    (
                        Transaction.type_ == TransactionType.BUY_PRODUCT,
                        -Transaction.product_count,
                    ),
                    (
                        Transaction.type_ == TransactionType.ADJUST_STOCK,
                        Transaction.product_count,
                    ),
                    else_=0,
                )
            )
        ).where(
            Transaction.type_.in_(
                [
                    TransactionType.BUY_PRODUCT,
                    TransactionType.ADD_PRODUCT,
                    TransactionType.ADJUST_STOCK,
                ]
            ),
            Transaction.product_id == product.id,
            Transaction.time <= until if until is not None else 1 == 1,
        )
    ).one_or_none()

    return result or 0

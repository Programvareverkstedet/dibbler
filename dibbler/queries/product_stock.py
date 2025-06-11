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
    # use_cache: bool = True,
    # until: datetime | None = None,
) -> int:
    """
    Returns the number of products in stock.
    """

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
        )
    ).one_or_none()

    return result or 0

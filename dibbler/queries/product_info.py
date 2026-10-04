from datetime import datetime
from typing import NamedTuple

from sqlalchemy import Integer, case, func, select
from sqlalchemy.orm import Session

from dibbler.models import Product, TransactionLog, TransactionLogProduct
from dibbler.models.enums import TransactionLogEntryType


class ProductInfo(NamedTuple):
    last_activity: datetime | None
    """The last time the product was involved in a transaction log entry."""

    times_bought: int
    """Total amount of items bought ever."""

    times_added: int
    """Total amount of items added ever."""

    stock_adjustments: int
    """Number of manual stock adjustments."""

    stock_adjustment_sum: int
    """Total change in stock due to manual adjustments."""


def product_info(
    sql_session: Session,
    product: Product,
    after_time: datetime | None = None,
    before_time: datetime | None = None,
) -> ProductInfo:
    """
    Retrieve various information about a product.

    Note that `after_time` is inclusive and `before_time` is exclusive.
    """

    if after_time is not None and before_time is not None and after_time > before_time:
        raise ValueError("after_time cannot be after before_time.")

    optional_conditions = [
        after_time is not None and TransactionLog.time >= after_time,
        before_time is not None and TransactionLog.time < before_time,
    ]
    conditions = [condition for condition in optional_conditions if not isinstance(condition, bool)]

    bought = func.sum(
        case(
            (
                TransactionLog.type == TransactionLogEntryType.BUY_PRODUCT,
                -TransactionLogProduct.amount,
            ),
            else_=0,
        ),
        type_=Integer,
    )
    added = func.sum(
        case(
            (
                TransactionLog.type == TransactionLogEntryType.ADD_PRODUCT,
                TransactionLogProduct.amount,
            ),
            else_=0,
        ),
        type_=Integer,
    )

    is_stock_adjustment = TransactionLog.type == TransactionLogEntryType.ADJUST_STOCK
    stock_adjustments = func.count(case((is_stock_adjustment, TransactionLogProduct.id)))
    stock_adjustment_sum = func.sum(
        case((is_stock_adjustment, TransactionLogProduct.amount), else_=0),
        type_=Integer,
    )

    query = (
        select(
            func.max(TransactionLog.time),
            func.coalesce(bought, 0),
            func.coalesce(added, 0),
            stock_adjustments,
            func.coalesce(stock_adjustment_sum, 0),
        )
        .select_from(TransactionLogProduct)
        .join(TransactionLogProduct.transaction)
        .where(TransactionLogProduct.product_id == product.id, *conditions)
    )

    return ProductInfo(*sql_session.execute(query).one())

from datetime import datetime

from sqlalchemy import (
    BindParameter,
    Select,
    and_,
    bindparam,
    case,
    func,
    or_,
    select,
)
from sqlalchemy.orm import Session

from dibbler.models import (
    LastCacheTransaction,
    Product,
    ProductCache,
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

    stock_delta = case(
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

    if use_cache:
        latest_cache = (
            select(
                ProductCache.stock.label("stock"),
                Transaction.time.label("transaction_time"),
                Transaction.id.label("transaction_id"),
            )
            .select_from(ProductCache)
            .join(
                LastCacheTransaction,
                ProductCache.last_cache_transaction_id == LastCacheTransaction.id,
            )
            .join(Transaction, LastCacheTransaction.transaction_id == Transaction.id)
            .where(
                ProductCache.product_id == product_id,
                until_filter(
                    until_time=until_time,
                    until_transaction_id=until_transaction_id,
                    until_inclusive=until_inclusive,
                    transaction_time=Transaction.time,
                ),
            )
            .order_by(Transaction.time.desc(), Transaction.id.desc(), ProductCache.id.desc())
            .limit(1)
            .subquery("latest_product_cache")
        )

        latest_cache_stock = select(latest_cache.c.stock).scalar_subquery()
        latest_cache_time = select(latest_cache.c.transaction_time).scalar_subquery()
        latest_cache_transaction_id = select(latest_cache.c.transaction_id).scalar_subquery()

        query = select(
            (
                func.coalesce(latest_cache_stock, 0)
                + func.coalesce(func.sum(stock_delta), 0)
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
            or_(
                latest_cache_time.is_(None),
                Transaction.time > latest_cache_time,
                and_(
                    Transaction.time == latest_cache_time,
                    Transaction.id > latest_cache_transaction_id,
                ),
            ),
        )
    else:
        query = select(
            func.coalesce(func.sum(stock_delta), 0).label("stock"),
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

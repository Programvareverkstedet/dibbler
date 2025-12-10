import math
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import (
    BindParameter,
    ColumnElement,
    Integer,
    bindparam,
    case,
    cast,
    func,
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
from dibbler.models.Transaction import DEFAULT_INTEREST_RATE_PERCENT
from dibbler.queries.query_helpers import (
    CONST_NONE,
    CONST_ONE,
    CONST_ZERO,
    after_filter,
    until_filter,
)


def _product_price_query(
    product_id: int | ColumnElement[int],
    use_cache: bool = True,
    until_time: BindParameter[datetime] | datetime | None = None,
    until_transaction: Transaction | None = None,
    until_inclusive: bool = True,
    cte_name: str = "rec_cte",
    trx_subset_name: str = "trx_subset",
):
    """
    The inner query for calculating the product price.
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

    if use_cache:
        initial_element_fields = (
            select(
                Transaction.time.label("time"),
                Transaction.id.label("transaction_id"),
                ProductCache.price.label("price"),
                ProductCache.stock.label("product_count"),
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
                ),
            )
            .union(
                select(
                    CONST_ZERO.label("time"),
                    CONST_NONE.label("transaction_id"),
                    CONST_ZERO.label("price"),
                    CONST_ZERO.label("product_count"),
                ),
            )
            .order_by(Transaction.time.desc())
            .limit(CONST_ONE)
            .offset(CONST_ZERO)
            .subquery()
            .alias("initial_element_fields")
        )

        initial_element = select(
            CONST_ZERO.label("i"),
            initial_element_fields.c.time,
            initial_element_fields.c.transaction_id,
            initial_element_fields.c.price,
            initial_element_fields.c.product_count,
        ).select_from(initial_element_fields)
    else:
        initial_element = select(
            CONST_ZERO.label("i"),
            CONST_ZERO.label("time"),
            CONST_NONE.label("transaction_id"),
            CONST_ZERO.label("price"),
            CONST_ZERO.label("product_count"),
        )

    recursive_cte = initial_element.cte(name=cte_name, recursive=True)

    # Subset of transactions that we'll want to iterate over.
    trx_subset = (
        select(
            func.row_number().over(order_by=Transaction.time.asc()).label("i"),
            Transaction.id,
            Transaction.time,
            Transaction.type_,
            Transaction.product_count,
            Transaction.per_product,
        )
        .where(
            Transaction.type_.in_(
                [
                    TransactionType.BUY_PRODUCT.as_literal_column(),
                    TransactionType.ADD_PRODUCT.as_literal_column(),
                    TransactionType.ADJUST_STOCK.as_literal_column(),
                    TransactionType.JOINT.as_literal_column(),
                ],
            ),
            Transaction.product_id == product_id,
            after_filter(
                after_time=None,
                after_transaction_id=recursive_cte.c.transaction_id,
                after_inclusive=False,
            ),
            until_filter(
                until_time=until_time,
                until_transaction_id=until_transaction_id,
                until_inclusive=until_inclusive,
            ),
        )
        .order_by(Transaction.time.asc())
        .subquery(trx_subset_name)
    )

    recursive_elements = (
        select(
            trx_subset.c.i,
            trx_subset.c.time,
            trx_subset.c.id.label("transaction_id"),
            case(
                # Someone buys the product -> price remains the same.
                (
                    trx_subset.c.type_ == TransactionType.BUY_PRODUCT.as_literal_column(),
                    recursive_cte.c.price,
                ),
                # Someone adds the product -> price is recalculated based on
                #  product count, previous price, and new price.
                (
                    trx_subset.c.type_ == TransactionType.ADD_PRODUCT.as_literal_column(),
                    cast(
                        func.ceil(
                            (
                                recursive_cte.c.price
                                * func.max(recursive_cte.c.product_count, CONST_ZERO)
                                + trx_subset.c.per_product * trx_subset.c.product_count
                            )
                            / (
                                # The running product count can be negative if the accounting is bad.
                                # This ensures that we never end up with negative prices or zero divisions
                                # and other disastrous phenomena.
                                func.max(recursive_cte.c.product_count, CONST_ZERO)
                                + trx_subset.c.product_count
                            ),
                        ),
                        Integer,
                    ),
                ),
                # Someone adjusts the stock -> price remains the same.
                (
                    trx_subset.c.type_ == TransactionType.ADJUST_STOCK.as_literal_column(),
                    recursive_cte.c.price,
                ),
                # Should never happen
                else_=recursive_cte.c.price,
            ).label("price"),
            case(
                # Someone buys the product -> product count is reduced.
                (
                    trx_subset.c.type_ == TransactionType.BUY_PRODUCT.as_literal_column(),
                    recursive_cte.c.product_count - trx_subset.c.product_count,
                ),
                (
                    trx_subset.c.type_ == TransactionType.JOINT.as_literal_column(),
                    recursive_cte.c.product_count - trx_subset.c.product_count,
                ),
                # Someone adds the product -> product count is increased.
                (
                    trx_subset.c.type_ == TransactionType.ADD_PRODUCT.as_literal_column(),
                    recursive_cte.c.product_count + trx_subset.c.product_count,
                ),
                # Someone adjusts the stock -> product count is adjusted.
                (
                    trx_subset.c.type_ == TransactionType.ADJUST_STOCK.as_literal_column(),
                    recursive_cte.c.product_count + trx_subset.c.product_count,
                ),
                # Should never happen
                else_=recursive_cte.c.product_count,
            ).label("product_count"),
        )
        .select_from(trx_subset)
        .where(trx_subset.c.i == recursive_cte.c.i + CONST_ONE)
    )

    return recursive_cte.union_all(recursive_elements)


# TODO: create a function for the log that pretty prints the log entries
#       for debugging purposes


@dataclass
class ProductPriceLogEntry:
    transaction: Transaction
    price: int
    product_count: int


def product_price_log(
    sql_session: Session,
    product: Product,
    use_cache: bool = True,
    until_time: BindParameter[datetime] | datetime | None = None,
    until_transaction: Transaction | None = None,
    until_inclusive: bool = True,
) -> list[ProductPriceLogEntry]:
    """
    Calculates the price of a product and returns a log of the price changes.
    """

    if product.id is None:
        raise ValueError("Product must be persisted in the database.")

    recursive_cte = _product_price_query(
        product.id,
        use_cache=use_cache,
        until_time=until_time,
        until_transaction=until_transaction,
        until_inclusive=until_inclusive,
    )

    result = sql_session.execute(
        select(
            Transaction,
            recursive_cte.c.price,
            recursive_cte.c.product_count,
        )
        .select_from(recursive_cte)
        .join(
            Transaction,
            onclause=Transaction.id == recursive_cte.c.transaction_id,
        )
        .order_by(recursive_cte.c.i.asc()),
    ).all()

    if result is None:
        # If there are no transactions for this product, the query should return an empty list, not None.
        raise RuntimeError(
            f"Something went wrong while calculating the price log for product {product.name} (ID: {product.id}).",
        )

    return [
        ProductPriceLogEntry(
            transaction=row[0],
            price=row.price,
            product_count=row.product_count,
        )
        for row in result
    ]


def product_price(
    sql_session: Session,
    product: Product,
    use_cache: bool = True,
    until_time: BindParameter[datetime] | datetime | None = None,
    until_transaction: Transaction | None = None,
    until_inclusive: bool = True,
    include_interest: bool = False,
) -> int:
    """
    Calculates the price of a product.
    """

    if product.id is None:
        raise ValueError("Product must be persisted in the database.")

    if isinstance(until_time, datetime):
        until_time = BindParameter("until_time", value=until_time)

    if isinstance(until_transaction, Transaction):
        if until_transaction.id is None:
            raise ValueError("until_transaction must be persisted in the database.")
        until_transaction_id = bindparam("until_transaction_id", value=until_transaction.id)
    else:
        until_transaction_id = None

    recursive_cte = _product_price_query(
        product.id,
        use_cache=use_cache,
        until_time=until_time,
        until_transaction=until_transaction,
        until_inclusive=until_inclusive,
    )

    # TODO: optionally verify subresults:
    #   - product_count should never be negative (but this happens sometimes, so just a warning)
    #   - price should never be negative

    result = sql_session.scalars(
        select(recursive_cte.c.price)
        .order_by(recursive_cte.c.i.desc())
        .limit(CONST_ONE)
        .offset(CONST_ZERO),
    ).one_or_none()

    if result is None:
        # If there are no transactions for this product, the query should return 0, not None.
        raise RuntimeError(
            f"Something went wrong while calculating the price for product {product.name} (ID: {product.id}).",
        )

    if include_interest:
        interest_rate = (
            sql_session.scalar(
                select(Transaction.interest_rate_percent)
                .where(
                    Transaction.type_ == TransactionType.ADJUST_INTEREST,
                    until_filter(
                        until_time=until_time,
                        until_transaction_id=until_transaction_id,
                        until_inclusive=until_inclusive,
                    ),
                )
                .order_by(Transaction.time.desc())
                .limit(CONST_ONE),
            )
            or DEFAULT_INTEREST_RATE_PERCENT
        )
        result = math.ceil(result * interest_rate / 100)

    return result

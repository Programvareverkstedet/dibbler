import math
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import (
    ColumnElement,
    Integer,
    SQLColumnExpression,
    asc,
    case,
    cast,
    func,
    literal,
    select,
)
from sqlalchemy.orm import Session

from dibbler.models import (
    Product,
    Transaction,
    TransactionType,
)
from dibbler.models.Transaction import DEFAULT_INTEREST_RATE_PERCENTAGE


def _product_price_query(
    product_id: int | ColumnElement[int],
    use_cache: bool = True,
    until: datetime | SQLColumnExpression[datetime] | None = None,
    until_including: bool = True,
    cte_name: str = "rec_cte",
):
    """
    The inner query for calculating the product price.
    """

    if use_cache:
        print("WARNING: Using cache for product price query is not implemented yet.")

    initial_element = select(
        literal(0).label("i"),
        literal(0).label("time"),
        literal(None).label("transaction_id"),
        literal(0).label("price"),
        literal(0).label("product_count"),
    )

    recursive_cte = initial_element.cte(name=cte_name, recursive=True)

    # Subset of transactions that we'll want to iterate over.
    trx_subset = (
        select(
            func.row_number().over(order_by=asc(Transaction.time)).label("i"),
            Transaction.id,
            Transaction.time,
            Transaction.type_,
            Transaction.product_count,
            Transaction.per_product,
        )
        .where(
            Transaction.type_.in_(
                [
                    TransactionType.BUY_PRODUCT,
                    TransactionType.ADD_PRODUCT,
                    TransactionType.ADJUST_STOCK,
                ]
            ),
            Transaction.product_id == product_id,
            case(
                (literal(until_including), Transaction.time <= until),
                else_=Transaction.time < until,
            )
            if until is not None
            else literal(True),
        )
        .order_by(Transaction.time.asc())
        .alias("trx_subset")
    )

    recursive_elements = (
        select(
            trx_subset.c.i,
            trx_subset.c.time,
            trx_subset.c.id.label("transaction_id"),
            case(
                # Someone buys the product -> price remains the same.
                (trx_subset.c.type_ == TransactionType.BUY_PRODUCT, recursive_cte.c.price),
                # Someone adds the product -> price is recalculated based on
                #  product count, previous price, and new price.
                (
                    trx_subset.c.type_ == TransactionType.ADD_PRODUCT,
                    cast(
                        func.ceil(
                            (
                                recursive_cte.c.price * func.max(recursive_cte.c.product_count, 0)
                                + trx_subset.c.per_product * trx_subset.c.product_count
                            )
                            / (
                                # The running product count can be negative if the accounting is bad.
                                # This ensures that we never end up with negative prices or zero divisions
                                # and other disastrous phenomena.
                                func.max(recursive_cte.c.product_count, 0)
                                + trx_subset.c.product_count
                            )
                        ),
                        Integer,
                    ),
                ),
                # Someone adjusts the stock -> price remains the same.
                (trx_subset.c.type_ == TransactionType.ADJUST_STOCK, recursive_cte.c.price),
                # Should never happen
                else_=recursive_cte.c.price,
            ).label("price"),
            case(
                # Someone buys the product -> product count is reduced.
                (
                    trx_subset.c.type_ == TransactionType.BUY_PRODUCT,
                    recursive_cte.c.product_count - trx_subset.c.product_count,
                ),
                # Someone adds the product -> product count is increased.
                (
                    trx_subset.c.type_ == TransactionType.ADD_PRODUCT,
                    recursive_cte.c.product_count + trx_subset.c.product_count,
                ),
                # Someone adjusts the stock -> product count is adjusted.
                (
                    trx_subset.c.type_ == TransactionType.ADJUST_STOCK,
                    recursive_cte.c.product_count + trx_subset.c.product_count,
                ),
                # Should never happen
                else_=recursive_cte.c.product_count,
            ).label("product_count"),
        )
        .select_from(trx_subset)
        .where(trx_subset.c.i == recursive_cte.c.i + 1)
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
    until: Transaction | None = None,
) -> list[ProductPriceLogEntry]:
    """
    Calculates the price of a product and returns a log of the price changes.
    """

    recursive_cte = _product_price_query(
        product.id,
        use_cache=use_cache,
        until=until.time if until else None,
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
        .order_by(recursive_cte.c.i.asc())
    ).all()

    if result is None:
        # If there are no transactions for this product, the query should return an empty list, not None.
        raise RuntimeError(
            f"Something went wrong while calculating the price log for product {product.name} (ID: {product.id})."
        )

    return [
        ProductPriceLogEntry(
            transaction=row[0],
            price=row.price,
            product_count=row.product_count,
        )
        for row in result
    ]


@staticmethod
def product_price(
    sql_session: Session,
    product: Product,
    use_cache: bool = True,
    until: Transaction | None = None,
    include_interest: bool = False,
) -> int:
    """
    Calculates the price of a product.
    """

    recursive_cte = _product_price_query(
        product.id,
        use_cache=use_cache,
        until=until.time if until else None,
    )

    # TODO: optionally verify subresults:
    #   - product_count should never be negative (but this happens sometimes, so just a warning)
    #   - price should never be negative

    result = sql_session.scalars(
        select(recursive_cte.c.price).order_by(recursive_cte.c.i.desc()).limit(1)
    ).one_or_none()

    if result is None:
        # If there are no transactions for this product, the query should return 0, not None.
        raise RuntimeError(
            f"Something went wrong while calculating the price for product {product.name} (ID: {product.id})."
        )

    if include_interest:
        interest_rate = (
            sql_session.scalar(
                select(Transaction.interest_rate_percent)
                .where(
                    Transaction.type_ == TransactionType.ADJUST_INTEREST,
                    literal(True) if until is None else Transaction.time <= until.time,
                )
                .order_by(Transaction.time.desc())
                .limit(1)
            )
            or DEFAULT_INTEREST_RATE_PERCENTAGE
        )
        result = math.ceil(result * interest_rate / 100)

    return result

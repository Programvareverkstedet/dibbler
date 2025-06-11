from datetime import datetime

from sqlalchemy import (
    Integer,
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

def _product_price_query(
    product: Product,
    # use_cache: bool = True,
    # until: datetime | None = None,
):
    """
    The inner query for calculating the product price.
    """
    initial_element = select(
        literal(0).label("i"),
        literal(0).label("time"),
        literal(0).label("price"),
        literal(0).label("product_count"),
    )

    recursive_cte = initial_element.cte(name="rec_cte", recursive=True)

    # Subset of transactions that we'll want to iterate over.
    trx_subset = (
        select(
            func.row_number().over(order_by=asc(Transaction.time)).label("i"),
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
            Transaction.product_id == product.id,
            # TODO:
            # If we have a transaction to limit the price calculation to, use it.
            # If not, use all transactions for the product.
            # (Transaction.time <= until.time) if until else True,
        )
        .order_by(Transaction.time.asc())
        .alias("trx_subset")
    )

    recursive_elements = (
        select(
            trx_subset.c.i,
            trx_subset.c.time,
            case(
                # Someone buys the product -> price remains the same.
                (trx_subset.c.type_ == TransactionType.BUY_PRODUCT, recursive_cte.c.price),
                # Someone adds the product -> price is recalculated based on
                #  product count, previous price, and new price.
                (
                    trx_subset.c.type_ == TransactionType.ADD_PRODUCT,
                    cast(
                        func.ceil(
                            (trx_subset.c.per_product * trx_subset.c.product_count)
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


def product_price_log(
    sql_session: Session,
    product: Product,
    # use_cache: bool = True,
    # Optional: calculate the price until a certain transaction.
    # until: Transaction | None = None,
) -> list[tuple[int, datetime, int, int]]:
    """
    Calculates the price of a product and returns a log of the price changes.
    """

    recursive_cte = _product_price_query(product)

    result = sql_session.execute(
        select(
            recursive_cte.c.i,
            recursive_cte.c.time,
            recursive_cte.c.price,
            recursive_cte.c.product_count,
        ).order_by(recursive_cte.c.i.asc())
    ).all()

    if not result:
        # If there are no transactions for this product, the query should return an empty list, not None.
        raise RuntimeError(
            f"Something went wrong while calculating the price log for product {product.name} (ID: {product.id})."
        )

    return [(row.i, row.time, row.price, row.product_count) for row in result]


@staticmethod
def product_price(
    sql_session: Session,
    product: Product,
    # use_cache: bool = True,
    # Optional: calculate the price until a certain transaction.
    # until: Transaction | None = None,
) -> int:
    """
    Calculates the price of a product.
    """

    recursive_cte = _product_price_query(product)  # , until=until)

    # TODO: optionally verify subresults:
    #   - product_count should never be negative (but this happens sometimes, so just a warning)
    #   - price should never be negative

    result = sql_session.scalar(
        select(recursive_cte.c.price).order_by(recursive_cte.c.i.desc()).limit(1)
    )

    if result is None:
        # If there are no transactions for this product, the query should return 0, not None.
        raise RuntimeError(
            f"Something went wrong while calculating the price for product {product.name} (ID: {product.id})."
        )

    return result

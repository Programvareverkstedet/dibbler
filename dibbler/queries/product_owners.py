from datetime import datetime

from sqlalchemy import (
    CTE,
    and_,
    asc,
    case,
    func,
    literal,
    select,
)
from sqlalchemy.orm import Session

from dibbler.models import (
    Product,
    Transaction,
    TransactionType,
    User,
)
from dibbler.queries.product_stock import _product_stock_query


def _product_owners_query(
    product_id: int,
    use_cache: bool = True,
    until: datetime | None = None,
    cte_name: str = "rec_cte",
) -> CTE:
    """
    The inner query for inferring the owners of a given product.
    """

    if use_cache:
        print("WARNING: Using cache for users owning product query is not implemented yet.")

    product_stock = _product_stock_query(
        product_id=product_id,
        use_cache=use_cache,
        until=until,
    )

    # Subset of transactions that we'll want to iterate over.
    trx_subset = (
        select(
          func.row_number().over(order_by=asc(Transaction.time)).label("i"),
          Transaction.time,
          Transaction.id,
          Transaction.type_,
          Transaction.user_id,
          Transaction.product_count, )
        .where(
            Transaction.type_.in_(
                [
                    TransactionType.ADD_PRODUCT,
                    TransactionType.BUY_PRODUCT,
                    TransactionType.ADJUST_STOCK,
                    TransactionType.JOINT,
                    TransactionType.THROW_PRODUCT,
                ]
            ),
            Transaction.product_id == product_id,
            literal(True) if until is None else Transaction.time <= until,
        )
        .order_by(Transaction.time.desc())
        .subquery()
    )

    initial_element = select(
        literal(0).label("i"),
        literal(0).label("time"),
        literal(None).label("transaction_id"),
        literal(None).label("user_id"),
        literal(0).label("product_count"),
        product_stock.scalar_subquery().label("products_left_to_account_for"),
    )

    recursive_cte = initial_element.cte(name=cte_name, recursive=True)

    recursive_elements = (
        select(
            trx_subset.c.i,
            trx_subset.c.time,
            trx_subset.c.id.label("transaction_id"),
            # Who added the product (if any)
            case(
                # Someone adds the product -> they own it
                (
                    trx_subset.c.type_ == TransactionType.ADD_PRODUCT,
                    trx_subset.c.user_id,
                ),
                else_=None,
            ).label("user_id"),
            # How many products did they add (if any)
            case(
                # Someone adds the product -> they added a certain amount of products
                (trx_subset.c.type_ == TransactionType.ADD_PRODUCT, trx_subset.c.product_count),
                # Stock got adjusted upwards -> consider those products as added by nobody
                (
                    (trx_subset.c.type_ == TransactionType.ADJUST_STOCK)
                    & (trx_subset.c.product_count > 0),
                    trx_subset.c.product_count,
                ),
                else_=None,
            ).label("product_count"),
            # How many products left to account for
            case(
                # Someone adds the product -> increase the number of products left to account for
                (
                    trx_subset.c.type_ == TransactionType.ADD_PRODUCT,
                    recursive_cte.c.products_left_to_account_for - trx_subset.c.product_count,
                ),
                # Someone buys/joins/throws the product -> decrease the number of products left to account for
                (
                    trx_subset.c.type_.in_(
                        [
                            TransactionType.BUY_PRODUCT,
                            TransactionType.JOINT,
                            TransactionType.THROW_PRODUCT,
                        ]
                    ),
                    recursive_cte.c.products_left_to_account_for - trx_subset.c.product_count,
                ),
                # Someone adjusts the stock ->
                #   If adjusted upwards -> products owned by nobody, decrease products left to account for
                #   If adjusted downwards -> products taken away from owners, decrease products left to account for
                (
                    (trx_subset.c.type_ == TransactionType.ADJUST_STOCK) and (trx_subset.c.product_count > 0),
                    recursive_cte.c.products_left_to_account_for - trx_subset.c.product_count,
                ),
                (
                    (trx_subset.c.type_ == TransactionType.ADJUST_STOCK) and (trx_subset.c.product_count < 0),
                    recursive_cte.c.products_left_to_account_for + trx_subset.c.product_count,
                ),
                else_=recursive_cte.c.products_left_to_account_for,
            ).label("products_left_to_account_for"),
        )
        .select_from(trx_subset)
        .where(
            and_(
                trx_subset.c.i == recursive_cte.c.i + 1,
                recursive_cte.c.products_left_to_account_for > 0,
            )
        )
    )

    return recursive_cte.union_all(recursive_elements)


def product_owners(
    sql_session: Session,
    product: Product,
    use_cache: bool = True,
    until: datetime | None = None,
) -> list[User | None]:
    """
    Returns an ordered list of users owning the given product.

    If 'until' is given, only transactions up to that time are considered.
    """

    recursive_cte = _product_owners_query(
        product_id=product.id,
        use_cache=use_cache,
        until=until,
    )

    db_result = sql_session.execute(
        select(
            recursive_cte.c.product_count,
            User,
        )
        .join(User, User.id == recursive_cte.c.user_id)
        .order_by(recursive_cte.c.i.desc())
    ).all()

    result: list[User | None] = []
    for user_count, user in db_result:
            result.extend([user] * user_count)

    # redistribute the user counts to a list of users

    return list(result)

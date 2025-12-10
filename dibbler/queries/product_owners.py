from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import (
    CTE,
    BindParameter,
    and_,
    bindparam,
    case,
    func,
    literal,
    select,
)
from sqlalchemy.orm import Session

from dibbler.lib.query_helpers import CONST_NONE, CONST_ONE, CONST_TRUE, CONST_ZERO, const
from dibbler.models import (
    Product,
    Transaction,
    TransactionType,
    User,
)
from dibbler.queries.product_stock import _product_stock_query


def _product_owners_query(
    product_id: BindParameter[int] | int,
    use_cache: bool = True,
    until: BindParameter[datetime] | datetime | None = None,
    cte_name: str = "rec_cte",
) -> CTE:
    """
    The inner query for inferring the owners of a given product.
    """

    if use_cache:
        print("WARNING: Using cache for users owning product query is not implemented yet.")

    if isinstance(product_id, int):
        product_id = bindparam("product_id", value=product_id)

    if isinstance(until, datetime):
        until = BindParameter("until", value=until)

    product_stock = _product_stock_query(
        product_id=product_id,
        use_cache=use_cache,
        until=until,
    )

    # Subset of transactions that we'll want to iterate over.
    trx_subset = (
        select(
            func.row_number().over(order_by=Transaction.time.desc()).label("i"),
            Transaction.time,
            Transaction.id,
            Transaction.type_,
            Transaction.user_id,
            Transaction.product_count,
        )
        # TODO: maybe add value constraint on ADJUST_STOCK?
        .where(
            Transaction.type_.in_(
                [
                    TransactionType.ADD_PRODUCT.as_literal_column(),
                    # TransactionType.BUY_PRODUCT,
                    TransactionType.ADJUST_STOCK.as_literal_column(),
                    # TransactionType.JOINT,
                    # TransactionType.THROW_PRODUCT,
                ]
            ),
            Transaction.product_id == product_id,
            CONST_TRUE if until is None else Transaction.time <= until,
        )
        .order_by(Transaction.time.desc())
        .subquery()
    )

    initial_element = select(
        CONST_ZERO.label("i"),
        CONST_ZERO.label("time"),
        CONST_NONE.label("transaction_id"),
        CONST_NONE.label("user_id"),
        CONST_ZERO.label("product_count"),
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
                    trx_subset.c.type_ == TransactionType.ADD_PRODUCT.as_literal_column(),
                    trx_subset.c.user_id,
                ),
                else_=CONST_NONE,
            ).label("user_id"),
            # How many products did they add (if any)
            case(
                # Someone adds the product -> they added a certain amount of products
                (
                    trx_subset.c.type_ == TransactionType.ADD_PRODUCT.as_literal_column(),
                    trx_subset.c.product_count,
                ),
                # Stock got adjusted upwards -> consider those products as added by nobody
                (
                    (trx_subset.c.type_ == TransactionType.ADJUST_STOCK.as_literal_column())
                    and (trx_subset.c.product_count > CONST_ZERO),
                    trx_subset.c.product_count,
                ),
                else_=CONST_ZERO,
            ).label("product_count"),
            # How many products left to account for
            case(
                # Someone adds the product -> increase the number of products left to account for
                (
                    trx_subset.c.type_ == TransactionType.ADD_PRODUCT.as_literal_column(),
                    recursive_cte.c.products_left_to_account_for - trx_subset.c.product_count,
                ),
                # Someone buys/joins/throws the product -> decrease the number of products left to account for
                # (
                #     trx_subset.c.type_.in_(
                #         [
                #             TransactionType.BUY_PRODUCT,
                #             TransactionType.JOINT,
                #             TransactionType.THROW_PRODUCT,
                #         ]
                #     ),
                #     recursive_cte.c.products_left_to_account_for - trx_subset.c.product_count,
                # ),
                # Someone adjusts the stock ->
                #   If adjusted upwards -> products owned by nobody, decrease products left to account for
                #   If adjusted downwards -> products taken away from owners, decrease products left to account for
                (
                    (trx_subset.c.type_ == TransactionType.ADJUST_STOCK.as_literal_column())
                    and (trx_subset.c.product_count > CONST_ZERO),
                    recursive_cte.c.products_left_to_account_for - trx_subset.c.product_count,
                ),
                # (
                #     (trx_subset.c.type_ == TransactionType.ADJUST_STOCK)
                #     and (trx_subset.c.product_count < 0),
                #     recursive_cte.c.products_left_to_account_for + trx_subset.c.product_count,
                # ),
                else_=recursive_cte.c.products_left_to_account_for,
            ).label("products_left_to_account_for"),
        )
        .select_from(trx_subset)
        .where(
            and_(
                trx_subset.c.i == recursive_cte.c.i + CONST_ONE,
                recursive_cte.c.products_left_to_account_for > CONST_ZERO,
            )
        )
    )

    return recursive_cte.union_all(recursive_elements)


@dataclass
class ProductOwnersLogEntry:
    transaction: Transaction
    user: User | None
    products_left_to_account_for: int


def product_owners_log(
    sql_session: Session,
    product: Product,
    use_cache: bool = True,
    until: Transaction | None = None,
) -> list[ProductOwnersLogEntry]:
    """
    Returns a log of the product ownership calculation for the given product.

    If 'until' is given, only transactions up to that time are considered.
    """

    recursive_cte = _product_owners_query(
        product_id=product.id,
        use_cache=use_cache,
        until=until.time if until else None,
    )

    result = sql_session.execute(
        select(
            Transaction,
            User,
            recursive_cte.c.products_left_to_account_for,
        )
        .select_from(recursive_cte)
        .join(
            Transaction,
            onclause=Transaction.id == recursive_cte.c.transaction_id,
        )
        .join(
            User,
            onclause=User.id == recursive_cte.c.user_id,
            isouter=True,
        )
        .order_by(recursive_cte.c.time.desc())
    ).all()

    if result is None:
        # If there are no transactions for this product, the query should return an empty list, not None.
        raise RuntimeError(
            f"Something went wrong while calculating the owner log for product {product.name} (ID: {product.id})."
        )

    return [
        ProductOwnersLogEntry(
            transaction=row[0],
            user=row[1],
            products_left_to_account_for=row[2],
        )
        for row in result
    ]


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
            recursive_cte.c.products_left_to_account_for,
            recursive_cte.c.product_count,
            User,
        )
        .join(User, User.id == recursive_cte.c.user_id, isouter=True)
        .order_by(recursive_cte.c.time.desc())
    ).all()

    print(db_result)

    result: list[User | None] = []
    none_count = 0

    # We are moving backwards through history, but this is the order we want to return the list
    # There are 3 cases:
    # User is not none -> add user product_count times
    # User is none, and product_count is not 0 -> add None product_count times
    # User is none, and product_count is 0 -> check how much products are left to account for,

    # TODO: embed this into the query itself?
    for products_left_to_account_for, product_count, user in db_result:
        if user is not None:
            if products_left_to_account_for < 0:
                result.extend([user] * (product_count + products_left_to_account_for))
            else:
                result.extend([user] * product_count)
        elif product_count != 0:
            if products_left_to_account_for < 0:
                none_count += product_count + products_left_to_account_for
            else:
                none_count += product_count
        else:
            pass

        #     none_count += user_count
        # else:

    result.extend([None] * none_count)

    # # NOTE: if the last line exeeds the product count, we need to truncate it
    # result.extend([user] * min(user_count, products_left_to_account_for))

    # redistribute the user counts to a list of users

    return list(result)

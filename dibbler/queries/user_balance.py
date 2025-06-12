from datetime import datetime

from sqlalchemy import (
    Integer,
    and_,
    asc,
    case,
    cast,
    column,
    func,
    literal,
    or_,
    select,
)
from sqlalchemy.orm import Session

from dibbler.models import (
    Transaction,
    TransactionType,
    User,
)
from dibbler.models.Transaction import (
    DEFAULT_INTEREST_RATE_PERCENTAGE,
    DEFAULT_PENALTY_MULTIPLIER_PERCENTAGE,
    DEFAULT_PENALTY_THRESHOLD,
)
from dibbler.queries.product_price import _product_price_query


def _user_balance_query(
    user: User,
    use_cache: bool = True,
    until: datetime | None = None,
    cte_name: str = "rec_cte",
):
    """
    The inner query for calculating the user's balance.
    """

    if use_cache:
        print("WARNING: Using cache for user balance query is not implemented yet.")

    initial_element = select(
        literal(0).label("i"),
        literal(0).label("time"),
        literal(0).label("balance"),
        literal(DEFAULT_INTEREST_RATE_PERCENTAGE).label("interest_rate_percent"),
        literal(DEFAULT_PENALTY_THRESHOLD).label("penalty_threshold"),
        literal(DEFAULT_PENALTY_MULTIPLIER_PERCENTAGE).label("penalty_multiplier_percent"),
    )

    recursive_cte = initial_element.cte(name=cte_name, recursive=True)

    # Subset of transactions that we'll want to iterate over.
    trx_subset = (
        select(
            func.row_number().over(order_by=asc(Transaction.time)).label("i"),
            Transaction.time,
            Transaction.type_,
            Transaction.amount,
            Transaction.product_count,
            Transaction.product_id,
            Transaction.transfer_user_id,
            Transaction.interest_rate_percent,
            Transaction.penalty_multiplier_percent,
            Transaction.penalty_threshold,
        )
        .where(
            or_(
                and_(
                    Transaction.user_id == user.id,
                    Transaction.type_.in_(
                        [
                            TransactionType.ADD_PRODUCT,
                            TransactionType.ADJUST_BALANCE,
                            TransactionType.BUY_PRODUCT,
                            TransactionType.TRANSFER,
                        ]
                    ),
                ),
                and_(
                    Transaction.type_ == TransactionType.TRANSFER,
                    Transaction.transfer_user_id == user.id,
                ),
                Transaction.type_.in_(
                    [
                        TransactionType.ADJUST_INTEREST,
                        TransactionType.ADJUST_PENALTY,
                    ]
                ),
            ),
            Transaction.time <= until if until is not None else 1 == 1,
        )
        .order_by(Transaction.time.asc())
        .alias("trx_subset")
    )

    recursive_elements = (
        select(
            trx_subset.c.i,
            trx_subset.c.time,
            case(
                # Adjusts balance -> balance gets adjusted
                (
                    trx_subset.c.type_ == TransactionType.ADJUST_BALANCE,
                    recursive_cte.c.balance + trx_subset.c.amount,
                ),
                # Adds a product -> balance increases
                (
                    trx_subset.c.type_ == TransactionType.ADD_PRODUCT,
                    recursive_cte.c.balance + trx_subset.c.amount,
                ),
                # Buys a product -> balance decreases
                (
                    trx_subset.c.type_ == TransactionType.BUY_PRODUCT,
                    recursive_cte.c.balance
                    - (
                        trx_subset.c.product_count
                        # Price of a single product, accounted for penalties and interest.
                        * cast(
                            func.ceil(
                                # TODO: This can get quite expensive real quick, so we should do some caching of the
                                #       product prices somehow.
                                # Base price
                                (
                                    select(column("price"))
                                    .select_from(
                                        _product_price_query(
                                            trx_subset.c.product_id,
                                            use_cache=use_cache,
                                            until=trx_subset.c.time,
                                            cte_name="product_price_cte",
                                        )
                                    )
                                    .order_by(column("i").desc())
                                    .limit(1)
                                ).scalar_subquery()
                                # TODO: should interest be applied before or after the penalty multiplier?
                                #       at the moment of writing, after sound right, but maybe ask someone?
                                # Interest
                                * (recursive_cte.c.interest_rate_percent / 100)
                                # Penalty
                                * case(
                                    (
                                        recursive_cte.c.balance < recursive_cte.c.penalty_threshold,
                                        (recursive_cte.c.penalty_multiplier_percent / 100),
                                    ),
                                    else_=1.0,
                                )
                            ),
                            Integer,
                        )
                    ),
                ),
                # Transfers money to self ->  balance increases
                (
                    trx_subset.c.type_ == TransactionType.TRANSFER
                    and trx_subset.c.transfer_user_id == user.id,
                    recursive_cte.c.balance + trx_subset.c.amount,
                ),
                # Transfers money from self ->  balance decreases
                (
                    trx_subset.c.type_ == TransactionType.TRANSFER
                    and trx_subset.c.transfer_user_id != user.id,
                    recursive_cte.c.balance - trx_subset.c.amount,
                ),
                # Interest adjustment -> balance stays the same
                # Penalty adjustment -> balance stays the same
                else_=recursive_cte.c.balance,
            ).label("balance"),
            case(
                (
                    trx_subset.c.type_ == TransactionType.ADJUST_INTEREST,
                    trx_subset.c.interest_rate_percent,
                ),
                else_=recursive_cte.c.interest_rate_percent,
            ).label("interest_rate_percent"),
            case(
                (
                    trx_subset.c.type_ == TransactionType.ADJUST_PENALTY,
                    trx_subset.c.penalty_threshold,
                ),
                else_=recursive_cte.c.penalty_threshold,
            ).label("penalty_threshold"),
            case(
                (
                    trx_subset.c.type_ == TransactionType.ADJUST_PENALTY,
                    trx_subset.c.penalty_multiplier_percent,
                ),
                else_=recursive_cte.c.penalty_multiplier_percent,
            ).label("penalty_multiplier_percent"),
        )
        .select_from(trx_subset)
        .where(trx_subset.c.i == recursive_cte.c.i + 1)
    )

    return recursive_cte.union_all(recursive_elements)


def user_balance_log(
    sql_session: Session,
    user: User,
    use_cache: bool = True,
    until: Transaction | None = None,
) -> list[tuple[int, datetime, int, int, int, int]]:
    recursive_cte = _user_balance_query(
        user,
        use_cache=use_cache,
        until=until.time if until else None,
    )

    result = sql_session.execute(
        select(
            recursive_cte.c.i,
            recursive_cte.c.time,
            recursive_cte.c.balance,
            recursive_cte.c.interest_rate_percent,
            recursive_cte.c.penalty_threshold,
            recursive_cte.c.penalty_multiplier_percent,
        ).order_by(recursive_cte.c.i.asc())
    ).all()

    if result is None:
        # If there are no transactions for this user, the query should return 0, not None.
        raise RuntimeError(
            f"Something went wrong while calculating the balance for user {user.name} (ID: {user.id})."
        )

    return result


def user_balance(
    sql_session: Session,
    user: User,
    use_cache: bool = True,
    # Optional: calculate the balance until a certain transaction.
    until: Transaction | None = None,
) -> int:
    """
    Calculates the balance of a user.
    """

    recursive_cte = _user_balance_query(
        user,
        use_cache=use_cache,
        until=until.time if until else None,
    )

    result = sql_session.scalar(
        select(recursive_cte.c.balance).order_by(recursive_cte.c.i.desc()).limit(1)
    )

    if result is None:
        # If there are no transactions for this user, the query should return 0, not None.
        raise RuntimeError(
            f"Something went wrong while calculating the balance for user {user.name} (ID: {user.id})."
        )

    return result

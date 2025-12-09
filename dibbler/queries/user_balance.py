from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import (
    Float,
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
    user_id: int,
    use_cache: bool = True,
    until: datetime | None = None,
    until_including: bool = True,
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
        literal(None).label("transaction_id"),
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
            Transaction.amount,
            Transaction.id,
            Transaction.interest_rate_percent,
            Transaction.penalty_multiplier_percent,
            Transaction.penalty_threshold,
            Transaction.product_count,
            Transaction.product_id,
            Transaction.time,
            Transaction.transfer_user_id,
            Transaction.type_,
        )
        .where(
            or_(
                and_(
                    Transaction.user_id == user_id,
                    Transaction.type_.in_(
                        [
                            TransactionType.ADD_PRODUCT,
                            TransactionType.ADJUST_BALANCE,
                            TransactionType.BUY_PRODUCT,
                            TransactionType.TRANSFER,
                            # TODO: join this with the JOINT transactions, and determine
                            #       how much the current user paid for the product.
                            TransactionType.JOINT_BUY_PRODUCT,
                        ]
                    ),
                ),
                and_(
                    Transaction.type_ == TransactionType.TRANSFER,
                    Transaction.transfer_user_id == user_id,
                ),
                Transaction.type_.in_(
                    [
                        TransactionType.THROW_PRODUCT,
                        TransactionType.ADJUST_INTEREST,
                        TransactionType.ADJUST_PENALTY,
                    ]
                ),
            ),
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
                                    # FIXME: this always returns 0 for some reason...
                                    select(cast(column("price"), Float))
                                    .select_from(
                                        _product_price_query(
                                            trx_subset.c.product_id,
                                            use_cache=use_cache,
                                            until=trx_subset.c.time,
                                            until_including=False,
                                            cte_name="product_price_cte",
                                        )
                                    )
                                    .order_by(column("i").desc())
                                    .limit(1)
                                ).scalar_subquery()
                                # TODO: should interest be applied before or after the penalty multiplier?
                                #       at the moment of writing, after sound right, but maybe ask someone?
                                # Interest
                                * (cast(recursive_cte.c.interest_rate_percent, Float) / 100)
                                # TODO: these should be added together, not multiplied, see specification
                                # Penalty
                                * case(
                                    (
                                        recursive_cte.c.balance < recursive_cte.c.penalty_threshold,
                                        (
                                            cast(recursive_cte.c.penalty_multiplier_percent, Float)
                                            / 100
                                        ),
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
                    and_(
                        trx_subset.c.type_ == TransactionType.TRANSFER,
                        trx_subset.c.transfer_user_id == user_id,
                    ),
                    recursive_cte.c.balance + trx_subset.c.amount,
                ),
                # Transfers money from self ->  balance decreases
                (
                    and_(
                        trx_subset.c.type_ == TransactionType.TRANSFER,
                        trx_subset.c.transfer_user_id != user_id,
                    ),
                    recursive_cte.c.balance - trx_subset.c.amount,
                ),
                # Throws a product -> if the user is considered to have bought it, balance increases
                # TODO:
                # (
                #     trx_subset.c.type_ == TransactionType.THROW_PRODUCT,
                #     recursive_cte.c.balance + trx_subset.c.amount,
                # ),

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


# TODO: create a function for the log that pretty prints the log entries
#       for debugging purposes


@dataclass
class UserBalanceLogEntry:
    transaction: Transaction
    balance: int
    interest_rate_percent: int
    penalty_threshold: int
    penalty_multiplier_percent: int

    def is_penalized(self) -> bool:
        """
        Returns whether this exact transaction is penalized.
        """

        return False

        # return self.transaction.type_ == TransactionType.BUY_PRODUCT and prev?


def user_balance_log(
    sql_session: Session,
    user: User,
    use_cache: bool = True,
    until: Transaction | None = None,
) -> list[UserBalanceLogEntry]:
    """
    Returns a log of the user's balance over time, including interest and penalty adjustments.
    """

    recursive_cte = _user_balance_query(
        user.id,
        use_cache=use_cache,
        until=until.time if until else None,
    )

    result = sql_session.execute(
        select(
            Transaction,
            recursive_cte.c.balance,
            recursive_cte.c.interest_rate_percent,
            recursive_cte.c.penalty_threshold,
            recursive_cte.c.penalty_multiplier_percent,
        )
        .select_from(recursive_cte)
        .join(
            Transaction,
            onclause=Transaction.id == recursive_cte.c.transaction_id,
        )
        .order_by(recursive_cte.c.i.asc())
    ).all()

    if result is None:
        # If there are no transactions for this user, the query should return 0, not None.
        raise RuntimeError(
            f"Something went wrong while calculating the balance for user {user.name} (ID: {user.id})."
        )

    return [
        UserBalanceLogEntry(
            transaction=row[0],
            balance=row.balance,
            interest_rate_percent=row.interest_rate_percent,
            penalty_threshold=row.penalty_threshold,
            penalty_multiplier_percent=row.penalty_multiplier_percent,
        )
        for row in result
    ]


def user_balance(
    sql_session: Session,
    user: User,
    use_cache: bool = True,
    until: Transaction | None = None,
) -> int:
    """
    Calculates the balance of a user.
    """

    recursive_cte = _user_balance_query(
        user.id,
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

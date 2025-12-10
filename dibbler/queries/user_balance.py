from dataclasses import dataclass
from datetime import datetime
from typing import Tuple

from sqlalchemy import (
    CTE,
    BindParameter,
    Float,
    Integer,
    Select,
    and_,
    bindparam,
    case,
    cast,
    column,
    func,
    or_,
    select,
)
from sqlalchemy.orm import Session, aliased
from sqlalchemy.sql.elements import KeyedColumnElement

from dibbler.models import (
    Transaction,
    TransactionType,
    User,
)
from dibbler.models.Transaction import (
    DEFAULT_INTEREST_RATE_PERCENT,
    DEFAULT_PENALTY_MULTIPLIER_PERCENT,
    DEFAULT_PENALTY_THRESHOLD,
)
from dibbler.queries.product_price import _product_price_query
from dibbler.queries.query_helpers import (
    CONST_NONE,
    CONST_ONE,
    CONST_ZERO,
    const,
    until_filter,
)


def _joint_transaction_query(
    user_id: BindParameter[int] | int,
    use_cache: bool = True,
    until_time: BindParameter[datetime] | None = None,
    until_transaction: Transaction | None = None,
    until_inclusive: bool = True,
) -> Select[tuple[int, int, int]]:
    """
    The inner query for getting joint transactions relevant to a user.

    This scans for JOINT_BUY_PRODUCT transactions made by the user,
    then finds the corresponding JOINT transactions, and counts how many "shares"
    of the joint transaction the user has, as well as the total number of shares.
    """

    if isinstance(until_transaction, Transaction):
        if until_transaction.id is None:
            raise ValueError("until_transaction must be persisted in the database.")
        until_transaction_id = bindparam("until_transaction_id", value=until_transaction.id)
    else:
        until_transaction_id = None

    # First, select all joint buy product transactions for the given user
    # sub_joint_transaction = aliased(Transaction, name="right_trx")
    sub_joint_transaction = (
        select(Transaction.joint_transaction_id.distinct().label("joint_transaction_id"))
        .where(
            Transaction.type_ == TransactionType.JOINT_BUY_PRODUCT.as_literal_column(),
            Transaction.user_id == user_id,
            until_filter(
                until_time=until_time,
                until_transaction_id=until_transaction_id,
                until_inclusive=until_inclusive,
                transaction_time=Transaction.time,
            ),
        )
        .subquery("sub_joint_transaction")
    )

    # Join those with their main joint transaction
    # (just use Transaction)

    # Then, count how many users are involved in each joint transaction
    joint_transaction_count = aliased(Transaction, name="count_trx")

    joint_transaction = (
        select(
            Transaction.id,
            # Shares the user has in the transaction,
            func.sum(
                case(
                    (joint_transaction_count.user_id == user_id, CONST_ONE),
                    else_=CONST_ZERO,
                ),
            ).label("user_shares"),
            # The total number of shares in the transaction,
            func.count(joint_transaction_count.id).label("user_count"),
        )
        .select_from(sub_joint_transaction)
        .join(
            Transaction,
            onclause=Transaction.id == sub_joint_transaction.c.joint_transaction_id,
        )
        .join(
            joint_transaction_count,
            onclause=joint_transaction_count.joint_transaction_id == Transaction.id,
        )
        .group_by(joint_transaction_count.joint_transaction_id)
    )

    return joint_transaction


def _non_joint_transaction_query(
    user_id: BindParameter[int] | int,
    use_cache: bool = True,
    until_time: BindParameter[datetime] | None = None,
    until_transaction: Transaction | None = None,
    until_inclusive: bool = True,
) -> Select[tuple[int, None, None]]:
    """
    The inner query for getting non-joint transactions relevant to a user.
    """

    if isinstance(until_transaction, Transaction):
        if until_transaction.id is None:
            raise ValueError("until_transaction must be persisted in the database.")
        until_transaction_id = bindparam("until_transaction_id", value=until_transaction.id)
    else:
        until_transaction_id = None

    query = select(
        Transaction.id,
        CONST_NONE.label("user_shares"),
        CONST_NONE.label("user_count"),
    ).where(
        or_(
            and_(
                Transaction.user_id == user_id,
                Transaction.type_.in_(
                    [
                        TransactionType.ADD_PRODUCT.as_literal_column(),
                        TransactionType.ADJUST_BALANCE.as_literal_column(),
                        TransactionType.BUY_PRODUCT.as_literal_column(),
                        TransactionType.TRANSFER.as_literal_column(),
                    ],
                ),
            ),
            and_(
                Transaction.type_ == TransactionType.TRANSFER.as_literal_column(),
                Transaction.transfer_user_id == user_id,
            ),
            Transaction.type_.in_(
                [
                    TransactionType.THROW_PRODUCT.as_literal_column(),
                    TransactionType.ADJUST_INTEREST.as_literal_column(),
                    TransactionType.ADJUST_PENALTY.as_literal_column(),
                ],
            ),
        ),
        until_filter(
            until_time=until_time,
            until_transaction_id=until_transaction_id,
            until_inclusive=until_inclusive,
        ),
    )

    return query


def _product_cost_expression(
    product_count_column: KeyedColumnElement[int],
    product_id_column: KeyedColumnElement[int],
    interest_rate_percent_column: KeyedColumnElement[int],
    user_balance_column: KeyedColumnElement[int],
    penalty_threshold_column: KeyedColumnElement[int],
    penalty_multiplier_percent_column: KeyedColumnElement[int],
    joint_user_shares_column: KeyedColumnElement[int],
    joint_user_count_column: KeyedColumnElement[int],
    use_cache: bool = True,
    until_time: BindParameter[datetime] | None = None,
    until_transaction: Transaction | None = None,
    until_inclusive: bool = True,
    cte_name: str = "product_price_cte",
    trx_subset_name: str = "product_price_trx_subset",
):
    # TODO: This can get quite expensive real quick, so we should do some caching of the
    #       product prices somehow.
    expression = (
        select(
            cast(
                func.ceil(
                    # Base price
                    (
                        cast(
                            column("price") * product_count_column * joint_user_shares_column,
                            Float,
                        )
                        / joint_user_count_column
                    )
                    # Interest
                    + (
                        cast(
                            column("price") * product_count_column * joint_user_shares_column,
                            Float,
                        )
                        / joint_user_count_column
                        * cast(interest_rate_percent_column - const(100), Float)
                        / const(100.0)
                    )
                    # Penalty
                    + (
                        (
                            cast(
                                column("price") * product_count_column * joint_user_shares_column,
                                Float,
                            )
                            / joint_user_count_column
                        )
                        * cast(penalty_multiplier_percent_column - const(100), Float)
                        / const(100.0)
                        * cast(user_balance_column < penalty_threshold_column, Integer)
                    ),
                ),
                Integer,
            ),
        )
        .select_from(
            _product_price_query(
                product_id_column,
                use_cache=use_cache,
                until_time=until_time,
                until_transaction=until_transaction,
                until_inclusive=until_inclusive,
                cte_name=cte_name,
                trx_subset_name=trx_subset_name,
            ),
        )
        .order_by(column("i").desc())
        .limit(CONST_ONE)
        .scalar_subquery()
    )

    return expression


def _user_balance_query(
    user_id: BindParameter[int] | int,
    use_cache: bool = True,
    until_time: BindParameter[datetime] | None = None,
    until_transaction: Transaction | None = None,
    until_inclusive: bool = True,
    cte_name: str = "rec_cte",
    trx_subset_name: str = "trx_subset",
) -> CTE:
    """
    The inner query for calculating the user's balance.
    """

    if use_cache:
        print("WARNING: Using cache for user balance query is not implemented yet.")

    if isinstance(user_id, int):
        user_id = BindParameter("user_id", value=user_id)

    initial_element = select(
        CONST_ZERO.label("i"),
        CONST_ZERO.label("time"),
        CONST_NONE.label("transaction_id"),
        CONST_ZERO.label("balance"),
        const(DEFAULT_INTEREST_RATE_PERCENT).label("interest_rate_percent"),
        const(DEFAULT_PENALTY_THRESHOLD).label("penalty_threshold"),
        const(DEFAULT_PENALTY_MULTIPLIER_PERCENT).label("penalty_multiplier_percent"),
    )

    recursive_cte = initial_element.cte(name=cte_name, recursive=True)

    trx_subset_subset = (
        _non_joint_transaction_query(
            user_id=user_id,
            use_cache=use_cache,
            until_time=until_time,
            until_transaction=until_transaction,
            until_inclusive=until_inclusive,
        )
        .union_all(
            _joint_transaction_query(
                user_id=user_id,
                use_cache=use_cache,
                until_time=until_time,
                until_transaction=until_transaction,
                until_inclusive=until_inclusive,
            ),
        )
        .subquery(f"{trx_subset_name}_subset")
    )

    # Subset of transactions that we'll want to iterate over.
    trx_subset = (
        select(
            func.row_number().over(order_by=Transaction.time.asc()).label("i"),
            Transaction.id,
            Transaction.amount,
            Transaction.interest_rate_percent,
            Transaction.penalty_multiplier_percent,
            Transaction.penalty_threshold,
            Transaction.product_count,
            Transaction.product_id,
            Transaction.time,
            Transaction.transfer_user_id,
            Transaction.type_,
            trx_subset_subset.c.user_shares,
            trx_subset_subset.c.user_count,
        )
        .select_from(trx_subset_subset)
        .join(
            Transaction,
            onclause=Transaction.id == trx_subset_subset.c.id,
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
                # Adjusts balance -> balance gets adjusted
                (
                    trx_subset.c.type_ == TransactionType.ADJUST_BALANCE.as_literal_column(),
                    recursive_cte.c.balance + trx_subset.c.amount,
                ),
                # Adds a product -> balance increases
                (
                    trx_subset.c.type_ == TransactionType.ADD_PRODUCT.as_literal_column(),
                    recursive_cte.c.balance + trx_subset.c.amount,
                ),
                # Buys a product -> balance decreases
                (
                    trx_subset.c.type_ == TransactionType.BUY_PRODUCT.as_literal_column(),
                    recursive_cte.c.balance
                    - _product_cost_expression(
                        product_count_column=trx_subset.c.product_count,
                        product_id_column=trx_subset.c.product_id,
                        interest_rate_percent_column=recursive_cte.c.interest_rate_percent,
                        user_balance_column=recursive_cte.c.balance,
                        penalty_threshold_column=recursive_cte.c.penalty_threshold,
                        penalty_multiplier_percent_column=recursive_cte.c.penalty_multiplier_percent,
                        joint_user_shares_column=CONST_ONE,
                        joint_user_count_column=CONST_ONE,
                        use_cache=use_cache,
                        until_time=until_time,
                        until_transaction=until_transaction,
                        until_inclusive=until_inclusive,
                        cte_name=f"{cte_name}_price",
                        trx_subset_name=f"{trx_subset_name}_price",
                    ).label("product_cost"),
                ),
                # Joint transaction -> balance decreases proportionally
                (
                    trx_subset.c.type_ == TransactionType.JOINT.as_literal_column(),
                    recursive_cte.c.balance
                    - _product_cost_expression(
                        product_count_column=trx_subset.c.product_count,
                        product_id_column=trx_subset.c.product_id,
                        interest_rate_percent_column=recursive_cte.c.interest_rate_percent,
                        user_balance_column=recursive_cte.c.balance,
                        penalty_threshold_column=recursive_cte.c.penalty_threshold,
                        penalty_multiplier_percent_column=recursive_cte.c.penalty_multiplier_percent,
                        joint_user_shares_column=trx_subset.c.user_shares,
                        joint_user_count_column=trx_subset.c.user_count,
                        use_cache=use_cache,
                        until_time=until_time,
                        until_transaction=until_transaction,
                        until_inclusive=until_inclusive,
                        cte_name=f"{cte_name}_joint_price",
                        trx_subset_name=f"{trx_subset_name}_joint_price",
                    ).label("joint_product_cost"),
                ),
                # Transfers money to self ->  balance increases
                (
                    and_(
                        trx_subset.c.type_ == TransactionType.TRANSFER.as_literal_column(),
                        trx_subset.c.transfer_user_id == user_id,
                    ),
                    recursive_cte.c.balance + trx_subset.c.amount,
                ),
                # Transfers money from self ->  balance decreases
                (
                    and_(
                        trx_subset.c.type_ == TransactionType.TRANSFER.as_literal_column(),
                        trx_subset.c.transfer_user_id != user_id,
                    ),
                    recursive_cte.c.balance - trx_subset.c.amount,
                ),
                # Throws a product -> if the user is considered to have bought it, balance increases
                # TODO: # (
                #     trx_subset.c.type_ == TransactionType.THROW_PRODUCT,
                #     recursive_cte.c.balance + trx_subset.c.amount,
                # ),
                # Interest adjustment -> balance stays the same
                # Penalty adjustment -> balance stays the same
                else_=recursive_cte.c.balance,
            ).label("balance"),
            case(
                (
                    trx_subset.c.type_ == TransactionType.ADJUST_INTEREST.as_literal_column(),
                    trx_subset.c.interest_rate_percent,
                ),
                else_=recursive_cte.c.interest_rate_percent,
            ).label("interest_rate_percent"),
            case(
                (
                    trx_subset.c.type_ == TransactionType.ADJUST_PENALTY.as_literal_column(),
                    trx_subset.c.penalty_threshold,
                ),
                else_=recursive_cte.c.penalty_threshold,
            ).label("penalty_threshold"),
            case(
                (
                    trx_subset.c.type_ == TransactionType.ADJUST_PENALTY.as_literal_column(),
                    trx_subset.c.penalty_multiplier_percent,
                ),
                else_=recursive_cte.c.penalty_multiplier_percent,
            ).label("penalty_multiplier_percent"),
        )
        .select_from(trx_subset)
        .where(trx_subset.c.i == recursive_cte.c.i + CONST_ONE)
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

        raise NotImplementedError("is_penalized is not implemented yet.")


def user_balance_log(
    sql_session: Session,
    user: User,
    use_cache: bool = True,
    until_time: BindParameter[datetime] | datetime | None = None,
    until_transaction: Transaction | None = None,
    until_inclusive: bool = True,
) -> list[UserBalanceLogEntry]:
    """
    Returns a log of the user's balance over time, including interest and penalty adjustments.

    If 'until' is given, only transactions up to that time are considered.
    """

    if user.id is None:
        raise ValueError("User must be persisted in the database.")

    if not (until_time is None or until_transaction is None):
        raise ValueError("Cannot filter by both until_time and until_transaction.")

    if isinstance(until_time, datetime):
        until_time = BindParameter("until_time", value=until_time)

    recursive_cte = _user_balance_query(
        user.id,
        use_cache=use_cache,
        until_time=until_time,
        until_transaction=until_transaction,
        until_inclusive=until_inclusive,
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
        .order_by(recursive_cte.c.i.asc()),
    ).all()

    if result is None:
        # If there are no transactions for this user, the query should return 0, not None.
        raise RuntimeError(
            f"Something went wrong while calculating the balance for user {user.name} (ID: {user.id}).",
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
    until_time: BindParameter[datetime] | datetime | None = None,
    until_transaction: Transaction | None = None,
    until_inclusive: bool = True,
) -> int:
    """
    Calculates the balance of a user.

    If 'until' is given, only transactions up to that time are considered.
    """

    if user.id is None:
        raise ValueError("User must be persisted in the database.")

    if not (until_time is None or until_transaction is None):
        raise ValueError("Cannot filter by both until_time and until_transaction.")

    if isinstance(until_time, datetime):
        until_time = BindParameter("until_time", value=until_time)

    recursive_cte = _user_balance_query(
        user.id,
        use_cache=use_cache,
        until_time=until_time,
        until_transaction=until_transaction,
        until_inclusive=until_inclusive,
    )

    result = sql_session.scalar(
        select(recursive_cte.c.balance)
        .order_by(recursive_cte.c.i.desc())
        .limit(CONST_ONE)
        .offset(CONST_ZERO),
    )

    if result is None:
        # If there are no transactions for this user, the query should return 0, not None.
        raise RuntimeError(
            f"Something went wrong while calculating the balance for user {user.name} (ID: {user.id}).",
        )

    return result

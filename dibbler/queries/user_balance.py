from sqlalchemy import func, select
from sqlalchemy.orm import Session

from dibbler.models import (
    Transaction,
    TransactionType,
    User,
)

# TODO: rename to 'balance' everywhere

def _user_balance_query(
    user: User,
    # use_cache: bool = True,
    # until: datetime | None = None,
):
    """
    The inner query for calculating the user's balance.
    """

    balance_adjustments = (
        select(func.coalesce(func.sum(Transaction.amount).label("balance_adjustments"), 0))
        .where(
            Transaction.user_id == user.id,
            Transaction.type_ == TransactionType.ADJUST_BALANCE,
        )
        .scalar_subquery()
    )

    transfers_to_other_users = (
        select(func.coalesce(func.sum(Transaction.amount).label("transfers_to_other_users"), 0))
        .where(
            Transaction.user_id == user.id,
            Transaction.type_ == TransactionType.TRANSFER,
        )
        .scalar_subquery()
    )

    transfers_to_self = (
        select(func.coalesce(func.sum(Transaction.amount).label("transfers_to_self"), 0))
        .where(
            Transaction.transfer_user_id == user.id,
            Transaction.type_ == TransactionType.TRANSFER,
        )
        .scalar_subquery()
    )

    add_products = (
        select(func.coalesce(func.sum(Transaction.amount).label("add_products"), 0))
        .where(
            Transaction.user_id == user.id,
            Transaction.type_ == TransactionType.ADD_PRODUCT,
        )
        .scalar_subquery()
    )

    buy_products = (
        select(func.coalesce(func.sum(Transaction.amount).label("buy_products"), 0))
        .where(
            Transaction.user_id == user.id,
            Transaction.type_ == TransactionType.BUY_PRODUCT,
        )
        .scalar_subquery()
    )

    query = select(
        # TODO: clearly define and fix the sign of the amount
        (
            0
            + balance_adjustments
            - transfers_to_other_users
            + transfers_to_self
            + add_products
            - buy_products
        ).label("balance")
    )

    return query


def user_balance(
    sql_session: Session,
    user: User,
    # use_cache: bool = True,
    # Optional: calculate the balance until a certain transaction.
    # until: Transaction | None = None,
) -> int:
    """
    Calculates the balance of a user.
    """

    query = _user_balance_query(user)  # , until=until)

    result = sql_session.scalar(query)

    if result is None:
        # If there are no transactions for this user, the query should return 0, not None.
        raise RuntimeError(
            f"Something went wrong while calculating the balance for user {user.name} (ID: {user.id})."
        )

    return result

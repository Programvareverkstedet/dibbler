from datetime import datetime
from typing import NamedTuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from dibbler.models import TransactionLog, TransactionLogUser, User, UserLog

from .._helpers import count_where, sum_where


class UserBalanceSummary(NamedTuple):
    positive_balance_count: int
    """Number of users with a positive balance."""

    zero_balance_count: int
    """Number of users with a zero balance."""

    negative_balance_count: int
    """Number of users with a negative balance."""

    positive_balance: int
    """Sum of the balances of users with a positive balance."""

    negative_balance: int
    """Sum of the balances of users with a negative balance."""

    @property
    def user_count(self) -> int:
        """Total number of users."""
        return self.positive_balance_count + self.zero_balance_count + self.negative_balance_count

    @property
    def total(self) -> int:
        """Total balance of all users."""
        return self.positive_balance + self.negative_balance


def summarize_user_balance(
    sql_session: Session,
    last_active_before: datetime | None = None,
) -> UserBalanceSummary:
    query = select(
        count_where(User.credit > 0),
        count_where(User.credit == 0),
        count_where(User.credit < 0),
        sum_where(User.credit > 0, User.credit),
        sum_where(User.credit < 0, User.credit),
    )

    if last_active_before is not None:
        query = query.where(
            ~select(TransactionLogUser)
            .join(TransactionLogUser.transaction)
            .where(
                TransactionLogUser.user_id == User.id,
                TransactionLog.time >= last_active_before,
            )
            .exists(),
            ~select(UserLog)
            .where(UserLog.user_id == User.id, UserLog.time >= last_active_before)
            .exists(),
        )

    return UserBalanceSummary(*sql_session.execute(query).one())

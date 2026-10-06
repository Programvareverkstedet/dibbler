from datetime import datetime
from typing import NamedTuple

from sqlalchemy import Integer, ScalarSelect, func, select
from sqlalchemy.orm import Session

from dibbler.models import TransactionLog, TransactionLogUser, User
from dibbler.models.enums import TransactionLogEntryType

from ._helpers import time_window_conditions
from .user_product_stats import user_product_stats_query


class UserInfo(NamedTuple):
    last_activity: datetime | None
    """The last time the user was involved in a transaction log entry."""

    products_bought: int
    """Total amount of items the user has bought ever."""

    products_added: int
    """Total amount of items the user has added ever."""

    stock_adjustments: int
    """Number of manual stock adjustments done by the user."""

    balance_adjustments: int
    """Number of manual balance adjustments done by the user."""

    balance_adjustment_sum: int
    """Total change in credit due to manual balance adjustments done by the user."""


def user_info(
    sql_session: Session,
    user: User,
    after_time: datetime | None = None,
    before_time: datetime | None = None,
) -> UserInfo:
    """
    Retrieve various information about a user.

    Note that `after_time` is inclusive and `before_time` is exclusive.
    """

    conditions = time_window_conditions(TransactionLog.time, after_time, before_time)

    last_activity = (
        select(func.max(TransactionLog.time))
        .where(TransactionLog.users.any(user=user), *conditions)
        .scalar_subquery()
    )

    def count_entries(entry_type: TransactionLogEntryType) -> ScalarSelect[int]:
        return (
            select(func.count(TransactionLog.id))
            .where(
                TransactionLog.type == entry_type,
                TransactionLog.users.any(user=user),
                *conditions,
            )
            .scalar_subquery()
        )

    balance_adjustment_sum = (
        select(func.coalesce(-func.sum(TransactionLogUser.amount, type_=Integer), 0))
        .join(TransactionLogUser.transaction)
        .where(
            TransactionLog.type == TransactionLogEntryType.ADJUST_BALANCE,
            TransactionLogUser.user_id == user.id,
            *conditions,
        )
        .scalar_subquery()
    )

    stats = user_product_stats_query(
        user=user,
        after_time=after_time,
        before_time=before_time,
    ).subquery()

    query = select(
        last_activity,
        func.coalesce(func.sum(stats.c.bought), 0),
        func.coalesce(func.sum(stats.c.added), 0),
        count_entries(TransactionLogEntryType.ADJUST_STOCK),
        count_entries(TransactionLogEntryType.ADJUST_BALANCE),
        balance_adjustment_sum,
    ).select_from(stats)

    return UserInfo(*sql_session.execute(query).one())

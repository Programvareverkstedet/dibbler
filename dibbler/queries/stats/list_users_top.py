from datetime import datetime
from typing import NamedTuple

from sqlalchemy import (
    ColumnElement,
    Integer,
    Select,
    SQLColumnExpression,
    func,
    select,
    type_coerce,
)
from sqlalchemy.orm import Session

from dibbler.models import TransactionLog, TransactionLogUser, User
from dibbler.models.enums import TransactionLogEntryType

from ._helpers import time_window_conditions


class UserCredit(NamedTuple):
    user: User
    credit: int


def _list_users_top_query(
    entry_type: TransactionLogEntryType,
    rank_by: SQLColumnExpression[int | None],
    conditions: list[ColumnElement[bool]],
    after_time: datetime | None,
    before_time: datetime | None,
) -> Select[tuple[User, int]]:
    total = type_coerce(func.sum(rank_by), Integer)

    return (
        select(User, total)
        .join(TransactionLogUser, TransactionLogUser.user_id == User.id)
        .join(TransactionLogUser.transaction)
        .where(
            TransactionLog.type == entry_type,
            *conditions,
            *time_window_conditions(TransactionLog.time, after_time, before_time),
        )
        .group_by(User.id)
        .order_by(total.desc(), User.id)
    )


def _list_users_top(
    sql_session: Session,
    query: Select[tuple[User, int]],
    limit: int | None,
) -> list[UserCredit]:
    if limit is not None and limit <= 0:
        raise ValueError("Limit must be positive.")

    return [UserCredit(*row) for row in sql_session.execute(query.limit(limit))]


def list_users_top_spending_query(
    after_time: datetime | None = None,
    before_time: datetime | None = None,
) -> Select[tuple[User, int]]:
    return _list_users_top_query(
        entry_type=TransactionLogEntryType.BUY_PRODUCT,
        rank_by=TransactionLogUser.amount,
        conditions=[],
        after_time=after_time,
        before_time=before_time,
    )


def list_users_top_spending(
    sql_session: Session,
    limit: int | None = 20,
    after_time: datetime | None = None,
    before_time: datetime | None = None,
) -> list[UserCredit]:
    """Top users by credit spent on purchases (including penalties)"""
    return _list_users_top(
        sql_session,
        list_users_top_spending_query(after_time, before_time),
        limit,
    )


def list_users_top_restocking_query(
    after_time: datetime | None = None,
    before_time: datetime | None = None,
) -> Select[tuple[User, int]]:
    return _list_users_top_query(
        entry_type=TransactionLogEntryType.ADD_PRODUCT,
        rank_by=-TransactionLogUser.amount,
        conditions=[],
        after_time=after_time,
        before_time=before_time,
    )


def list_users_top_restocking(
    sql_session: Session,
    limit: int | None = 20,
    after_time: datetime | None = None,
    before_time: datetime | None = None,
) -> list[UserCredit]:
    """Top users by credit received for adding stock."""
    return _list_users_top(
        sql_session,
        list_users_top_restocking_query(after_time, before_time),
        limit,
    )


def list_users_top_depositing_query(
    after_time: datetime | None = None,
    before_time: datetime | None = None,
) -> Select[tuple[User, int]]:
    return _list_users_top_query(
        entry_type=TransactionLogEntryType.ADJUST_BALANCE,
        rank_by=-TransactionLogUser.amount,
        conditions=[TransactionLogUser.amount < 0],
        after_time=after_time,
        before_time=before_time,
    )


def list_users_top_depositing(
    sql_session: Session,
    limit: int | None = 20,
    after_time: datetime | None = None,
    before_time: datetime | None = None,
) -> list[UserCredit]:
    """Top users by credit deposited through balance adjustments."""
    return _list_users_top(
        sql_session,
        list_users_top_depositing_query(after_time, before_time),
        limit,
    )


def list_users_top_withdrawing_query(
    after_time: datetime | None = None,
    before_time: datetime | None = None,
) -> Select[tuple[User, int]]:
    return _list_users_top_query(
        entry_type=TransactionLogEntryType.ADJUST_BALANCE,
        rank_by=TransactionLogUser.amount,
        conditions=[TransactionLogUser.amount > 0],
        after_time=after_time,
        before_time=before_time,
    )


def list_users_top_withdrawing(
    sql_session: Session,
    limit: int | None = 20,
    after_time: datetime | None = None,
    before_time: datetime | None = None,
) -> list[UserCredit]:
    """Top users by credit withdrawn through balance adjustments."""
    return _list_users_top(
        sql_session,
        list_users_top_withdrawing_query(after_time, before_time),
        limit,
    )

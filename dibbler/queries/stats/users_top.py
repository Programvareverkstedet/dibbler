from collections.abc import Iterator
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

from dibbler.lib.sql_helpers import DEFAULT_STREAMING_ITER_CHUNK_SIZE, iter_rows_in_chunks
from dibbler.models import TransactionLog, TransactionLogUser, User
from dibbler.models.enums import TransactionLogEntryType

from ._helpers import time_window_conditions


class UserCredit(NamedTuple):
    user: User
    credit: int


def _users_top_query(
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


def _users_top_list(
    sql_session: Session,
    query: Select[tuple[User, int]],
    limit: int | None,
) -> list[UserCredit]:
    if limit is not None and limit <= 0:
        raise ValueError("Limit must be positive.")

    return [UserCredit(*row) for row in sql_session.execute(query.limit(limit))]


def _users_top_stream(
    sql_session: Session,
    query: Select[tuple[User, int]],
    chunk_size: int,
) -> Iterator[UserCredit]:
    return (UserCredit(*row) for row in iter_rows_in_chunks(sql_session, query, chunk_size))


def users_top_spending_query(
    after_time: datetime | None = None,
    before_time: datetime | None = None,
) -> Select[tuple[User, int]]:
    return _users_top_query(
        entry_type=TransactionLogEntryType.BUY_PRODUCT,
        rank_by=TransactionLogUser.amount,
        conditions=[],
        after_time=after_time,
        before_time=before_time,
    )


def users_top_spending_list(
    sql_session: Session,
    limit: int | None = 20,
    after_time: datetime | None = None,
    before_time: datetime | None = None,
) -> list[UserCredit]:
    """Top users by credit spent on purchases (including penalties)"""
    return _users_top_list(
        sql_session,
        users_top_spending_query(after_time, before_time),
        limit,
    )


def users_top_spending_stream(
    sql_session: Session,
    after_time: datetime | None = None,
    before_time: datetime | None = None,
    chunk_size: int = DEFAULT_STREAMING_ITER_CHUNK_SIZE,
) -> Iterator[UserCredit]:
    """
    Streaming variant of `users_top_spending_list`, which fetches `chunk_size` users at a time.
    """
    return _users_top_stream(
        sql_session,
        users_top_spending_query(after_time, before_time),
        chunk_size,
    )


def users_top_restocking_query(
    after_time: datetime | None = None,
    before_time: datetime | None = None,
) -> Select[tuple[User, int]]:
    return _users_top_query(
        entry_type=TransactionLogEntryType.ADD_PRODUCT,
        rank_by=-TransactionLogUser.amount,
        conditions=[],
        after_time=after_time,
        before_time=before_time,
    )


def users_top_restocking_list(
    sql_session: Session,
    limit: int | None = 20,
    after_time: datetime | None = None,
    before_time: datetime | None = None,
) -> list[UserCredit]:
    """Top users by credit received for adding stock."""
    return _users_top_list(
        sql_session,
        users_top_restocking_query(after_time, before_time),
        limit,
    )


def users_top_restocking_stream(
    sql_session: Session,
    after_time: datetime | None = None,
    before_time: datetime | None = None,
    chunk_size: int = DEFAULT_STREAMING_ITER_CHUNK_SIZE,
) -> Iterator[UserCredit]:
    """
    Streaming variant of `users_top_restocking_list`, which fetches `chunk_size` users at a time.
    Unlike `users_top_restocking_list`, every matching user is included.
    """
    return _users_top_stream(
        sql_session,
        users_top_restocking_query(after_time, before_time),
        chunk_size,
    )


def users_top_depositing_query(
    after_time: datetime | None = None,
    before_time: datetime | None = None,
) -> Select[tuple[User, int]]:
    return _users_top_query(
        entry_type=TransactionLogEntryType.ADJUST_BALANCE,
        rank_by=-TransactionLogUser.amount,
        conditions=[TransactionLogUser.amount < 0],
        after_time=after_time,
        before_time=before_time,
    )


def users_top_depositing_list(
    sql_session: Session,
    limit: int | None = 20,
    after_time: datetime | None = None,
    before_time: datetime | None = None,
) -> list[UserCredit]:
    """Top users by credit deposited through balance adjustments."""
    return _users_top_list(
        sql_session,
        users_top_depositing_query(after_time, before_time),
        limit,
    )


def users_top_depositing_stream(
    sql_session: Session,
    after_time: datetime | None = None,
    before_time: datetime | None = None,
    chunk_size: int = DEFAULT_STREAMING_ITER_CHUNK_SIZE,
) -> Iterator[UserCredit]:
    """
    Streaming variant of `users_top_depositing_list`, which fetches `chunk_size` users at a time.
    Unlike `users_top_depositing_list`, every matching user is included.
    """
    return _users_top_stream(
        sql_session,
        users_top_depositing_query(after_time, before_time),
        chunk_size,
    )


def users_top_withdrawing_query(
    after_time: datetime | None = None,
    before_time: datetime | None = None,
) -> Select[tuple[User, int]]:
    return _users_top_query(
        entry_type=TransactionLogEntryType.ADJUST_BALANCE,
        rank_by=TransactionLogUser.amount,
        conditions=[TransactionLogUser.amount > 0],
        after_time=after_time,
        before_time=before_time,
    )


def users_top_withdrawing_list(
    sql_session: Session,
    limit: int | None = 20,
    after_time: datetime | None = None,
    before_time: datetime | None = None,
) -> list[UserCredit]:
    """Top users by credit withdrawn through balance adjustments."""
    return _users_top_list(
        sql_session,
        users_top_withdrawing_query(after_time, before_time),
        limit,
    )


def users_top_withdrawing_stream(
    sql_session: Session,
    after_time: datetime | None = None,
    before_time: datetime | None = None,
    chunk_size: int = DEFAULT_STREAMING_ITER_CHUNK_SIZE,
) -> Iterator[UserCredit]:
    """
    Streaming variant of `users_top_withdrawing_list`, which fetches `chunk_size` users at a time.
    Unlike `users_top_withdrawing_list`, every matching user is included.
    """
    return _users_top_stream(
        sql_session,
        users_top_withdrawing_query(after_time, before_time),
        chunk_size,
    )

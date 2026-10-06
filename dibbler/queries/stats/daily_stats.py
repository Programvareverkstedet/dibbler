from collections.abc import Iterator
from dataclasses import dataclass, fields
from datetime import date, datetime, time, timedelta
from typing import Any

from sqlalchemy import (
    ColumnElement,
    CompoundSelect,
    Date,
    Integer,
    Select,
    SQLColumnExpression,
    and_,
    case,
    func,
    literal,
    select,
    union_all,
)
from sqlalchemy.orm import Session

from dibbler.models import (
    ProductLog,
    TransactionLog,
    TransactionLogProduct,
    TransactionLogUser,
    UserLog,
)
from dibbler.models.enums import ProductLogEntryType, TransactionLogEntryType, UserLogEntryType

from .._helpers import DEFAULT_STREAMING_ITER_CHUNK_SIZE, add_days, time_window_conditions

UNSET: Any = object()


@dataclass(frozen=True)
class DailyStats:
    day: date
    """The day for which the statistics are collected."""

    sold_amount: int
    """Total number of units sold, negative for stock decrease."""

    added_amount: int
    """Total number of units added, positive for stock increase."""

    sold_credit: int
    """Total credit earned from sales, negative for user credit decrease."""

    added_credit: int
    """Total credit added to users, positive for user credit increase."""

    transaction_count: int
    """Total number of transactions logged."""

    penalized_purchase_count: int
    """Total number of purchases where at least one buyer had a penalty."""

    new_product_count: int
    """Total number of new products created."""

    new_user_count: int
    """Total number of new users created."""

    def __post_init__(self) -> None:
        assert self.sold_amount <= 0, f"sold_amount must not be positive: {self}"
        assert self.added_amount >= 0, f"added_amount must not be negative: {self}"
        assert self.sold_credit <= 0, f"sold_credit must not be positive: {self}"
        assert self.added_credit >= 0, f"added_credit must not be negative: {self}"
        assert self.transaction_count >= 0, f"transaction_count must not be negative: {self}"
        assert 0 <= self.penalized_purchase_count <= self.transaction_count, (
            f"penalized_purchase_count must be between 0 and transaction_count: {self}"
        )
        assert self.new_product_count >= 0, f"new_product_count must not be negative: {self}"
        assert self.new_user_count >= 0, f"new_user_count must not be negative: {self}"


_COLUMNS = tuple(field.name for field in fields(DailyStats))[1:]


def _row(
    time: SQLColumnExpression[datetime],
    **values: ColumnElement[int] | int,
) -> list[ColumnElement[date] | ColumnElement[int]]:
    """
    Fills out the remaining non-specified columns with 0, so that the union of multiple rows
    can be summed up and grouped by day.
    """
    if unknown := values.keys() - set(_COLUMNS):
        raise ValueError(f"Unknown columns: {unknown}")

    columns: list[ColumnElement[date] | ColumnElement[int]] = [
        func.date(time, type_=Date).label("day"),
    ]
    for name in _COLUMNS:
        value = values.get(name, 0)
        if isinstance(value, int):
            value = literal(value, Integer)
        columns.append(value.label(name))
    return columns


def _activity(
    after_time: datetime | None,
    before_time: datetime | None,
) -> CompoundSelect[tuple[date, int, int, int, int, int, int, int, int]]:
    product_rows = (
        select(
            *_row(
                TransactionLog.time,
                sold_amount=case(
                    (
                        TransactionLog.type == TransactionLogEntryType.BUY_PRODUCT,
                        TransactionLogProduct.amount,
                    ),
                    else_=0,
                ),
                added_amount=case(
                    (
                        TransactionLog.type == TransactionLogEntryType.ADD_PRODUCT,
                        TransactionLogProduct.amount,
                    ),
                    else_=0,
                ),
            ),
        )
        .join(TransactionLog.products)
        .where(
            *time_window_conditions(TransactionLog.time, after_time, before_time),
        )
    )
    user_rows = (
        select(
            *_row(
                TransactionLog.time,
                sold_credit=case(
                    (
                        TransactionLog.type == TransactionLogEntryType.BUY_PRODUCT,
                        -TransactionLogUser.amount,
                    ),
                    else_=0,
                ),
                added_credit=case(
                    (
                        TransactionLog.type == TransactionLogEntryType.ADD_PRODUCT,
                        -TransactionLogUser.amount,
                    ),
                    else_=0,
                ),
            ),
        )
        .join(TransactionLog.users)
        .where(
            *time_window_conditions(TransactionLog.time, after_time, before_time),
        )
    )
    transaction_rows = select(
        *_row(
            TransactionLog.time,
            transaction_count=1,
            penalized_purchase_count=case(
                (
                    and_(
                        TransactionLog.type == TransactionLogEntryType.BUY_PRODUCT,
                        TransactionLog.users.any(TransactionLogUser.penalty > 1),
                    ),
                    1,
                ),
                else_=0,
            ),
        ),
    ).where(
        *time_window_conditions(TransactionLog.time, after_time, before_time),
    )

    new_product_rows = select(
        *_row(ProductLog.time, new_product_count=1),
    ).where(
        ProductLog.type == ProductLogEntryType.CREATE,
        *time_window_conditions(ProductLog.time, after_time, before_time),
    )
    new_user_rows = select(
        *_row(UserLog.time, new_user_count=1),
    ).where(
        UserLog.type == UserLogEntryType.CREATE,
        *time_window_conditions(UserLog.time, after_time, before_time),
    )

    return union_all(
        product_rows,
        user_rows,
        transaction_rows,
        new_product_rows,
        new_user_rows,
    )


def _last_day(before_time: datetime | None) -> date:
    """The last day with any time before `before_time`, or today if `before_time` is unset."""
    return (before_time - timedelta(seconds=1)).date() if before_time is not None else date.today()


def _default_after_time(before_time: datetime | None) -> datetime:
    """The start of the 30 days up to and including `_last_day(before_time)`."""
    return datetime.combine(_last_day(before_time) - timedelta(days=29), time.min)


def daily_stats_query(
    after_time: datetime | None = UNSET,
    before_time: datetime | None = None,
    newest_first: bool = False,
) -> Select[tuple[date, int, int, int, int, int, int, int, int]]:
    if after_time is UNSET:
        after_time = _default_after_time(before_time)

    activity = _activity(after_time, before_time).cte("activity")

    # NOTE: in order to include days with no activity, we need to generate a list of all
    #       days in the requested time window. In SQL, we can do this with a recursive CTE.
    first_day = (
        literal(after_time.date(), Date)
        if after_time is not None
        else select(func.min(activity.c.day)).scalar_subquery()
    )
    last_day = _last_day(before_time)

    days = select(first_day.label("day")).where(first_day <= last_day).cte("days", recursive=True)
    days = days.union_all(
        select(add_days(days.c.day, 1)).where(days.c.day < last_day),
    )

    return (
        select(
            days.c.day,
            *(
                func.coalesce(func.sum(activity.c[name]), 0, type_=Integer).label(name)
                for name in _COLUMNS
            ),
        )
        .select_from(days)
        .outerjoin(activity, activity.c.day == days.c.day)
        .group_by(days.c.day)
        .order_by(days.c.day.desc() if newest_first else days.c.day)
    )


def daily_stats_list(
    sql_session: Session,
    after_time: datetime | None = UNSET,
    before_time: datetime | None = None,
    newest_first: bool = False,
) -> list[DailyStats]:
    """
    Activity grouped by day.

    - `after_time` is inclusive and `before_time` is exclusive.
    - `after_time` defaults to 30 days before `before_time`, so that the window covers the 30
      days up to `before_time`, or the last 30 days including today if `before_time` is unset.
      You can pass `None` to include all history.
    """
    query = daily_stats_query(after_time, before_time, newest_first)
    return [DailyStats(*row) for row in sql_session.execute(query)]


def _day_windows(
    after_time: datetime,
    before_time: datetime,
    days: int,
    reverse: bool = False,
) -> Iterator[tuple[datetime, datetime]]:
    """
    Cut up the time interval into consecutive windows in intervals of `days` days.
    The intervals are cut at midnight.

    Day windows are ordered from oldest to newest by default.
    """
    step = timedelta(days=days)
    if reverse:
        end = before_time
        start = datetime.combine(_last_day(end), time.min) - step + timedelta(days=1)
        while start > after_time:
            yield start, end
            end = start
            start -= step
        yield after_time, end
    else:
        start = after_time
        end = datetime.combine(after_time.date(), time.min) + step
        while end < before_time:
            yield start, end
            start = end
            end += step
        yield start, before_time


def _daily_stats_stream(
    sql_session: Session,
    after_time: datetime | None,
    before_time: datetime | None,
    newest_first: bool,
    chunk_size: int,
) -> Iterator[DailyStats]:
    if after_time is None:
        activity = _activity(None, before_time).subquery()
        first_day = sql_session.scalar(select(func.min(activity.c.day)))
        if first_day is None:
            return
        after_time = datetime.combine(first_day, time.min)

    if before_time is None:
        # NOTE: setting before_time to the future is essentially the same as None
        before_time = datetime.combine(date.today() + timedelta(days=1), time.min)

    # NOTE: This could happend if someone passes an after_time in the future.
    if after_time > before_time:
        return

    for window_after_time, window_before_time in _day_windows(
        after_time,
        before_time,
        chunk_size,
        reverse=newest_first,
    ):
        query = daily_stats_query(window_after_time, window_before_time, newest_first)
        for row in sql_session.execute(query):
            yield DailyStats(*row)


def daily_stats_stream(
    sql_session: Session,
    after_time: datetime | None = UNSET,
    before_time: datetime | None = None,
    newest_first: bool = False,
    chunk_size: int = DEFAULT_STREAMING_ITER_CHUNK_SIZE,
) -> Iterator[DailyStats]:
    """
    Streaming variant of `daily_stats_list`, which fetches `chunk_size` days at a time.

    Each chunk is a separate query limited to its own days, so that it only has to
    go through the activity of those days.
    """
    if chunk_size <= 0:
        raise ValueError("Chunk size must be positive.")

    if after_time is UNSET:
        after_time = _default_after_time(before_time)

    if after_time is not None and before_time is not None and after_time > before_time:
        raise ValueError("after_time cannot be after before_time.")

    # TODO: assert that after_time is not set in the future?

    return _daily_stats_stream(sql_session, after_time, before_time, newest_first, chunk_size)

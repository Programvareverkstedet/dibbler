from datetime import datetime

from sqlalchemy import ColumnElement, Integer, SQLColumnExpression, case, func


def time_window_conditions(
    column: SQLColumnExpression[datetime],
    after_time: datetime | None,
    before_time: datetime | None,
) -> list[ColumnElement[bool]]:
    """
    Conditions limiting `column` to the given time window.

    `after_time` is inclusive and `before_time` is exclusive.
    """

    if after_time is not None and before_time is not None and after_time > before_time:
        raise ValueError("after_time cannot be after before_time.")

    conditions = []
    if after_time is not None:
        conditions.append(column >= after_time)
    if before_time is not None:
        conditions.append(column < before_time)
    return conditions


def count_where(condition: ColumnElement[bool]) -> ColumnElement[int]:
    """Number of rows matching `condition`."""
    return func.count(case((condition, 1)))


def sum_where(
    condition: ColumnElement[bool],
    value: SQLColumnExpression[int],
) -> ColumnElement[int]:
    """Sum of `value` over rows matching `condition`, or 0 if there are none."""
    return func.coalesce(func.sum(case((condition, value))), 0, type_=Integer)

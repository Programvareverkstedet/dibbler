from datetime import date, datetime
from typing import Any

from sqlalchemy import ColumnElement, Date, Integer, SQLColumnExpression, case, func, literal
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql.compiler import SQLCompiler
from sqlalchemy.sql.functions import FunctionElement


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


class add_days(FunctionElement[date]):  # noqa: N801
    """
    `day` plus `days` days.

    This is a custom SQL function which differs by dialect.
    """

    type = Date()
    inherit_cache = True

    def __init__(self, day: SQLColumnExpression[date], days: int) -> None:
        super().__init__(day, literal(days, Integer))


@compiles(add_days)
def _compile_add_days(
    element: add_days,
    compiler: SQLCompiler,
    **kw: Any,  # noqa: ANN401
) -> str:
    day, days = element.clauses
    return f"({compiler.process(day, **kw)} + {compiler.process(days, **kw)})"


@compiles(add_days, "sqlite")
def _compile_add_days_sqlite(
    element: add_days,
    compiler: SQLCompiler,
    **kw: Any,  # noqa: ANN401
) -> str:
    day, days = element.clauses
    return f"date({compiler.process(day, **kw)}, {compiler.process(days, **kw)} || ' days')"

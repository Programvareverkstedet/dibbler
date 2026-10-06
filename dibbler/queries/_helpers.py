from collections.abc import Iterator, Sequence
from datetime import date, datetime
from typing import Any, TypeVar

from sqlalchemy import (
    ColumnElement,
    Date,
    Integer,
    Row,
    Select,
    SQLColumnExpression,
    case,
    func,
    literal,
    tuple_,
)
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import InstrumentedAttribute, Session
from sqlalchemy.sql.compiler import SQLCompiler
from sqlalchemy.sql.functions import FunctionElement

T = TypeVar("T")
TupleT = TypeVar("TupleT", bound=tuple[Any, ...])

DEFAULT_STREAMING_ITER_CHUNK_SIZE = 64


def iter_rows_in_chunks(
    sql_session: Session,
    query: Select[TupleT],
    chunk_size: int = DEFAULT_STREAMING_ITER_CHUNK_SIZE,
) -> Iterator[Row[TupleT]]:
    """
    Create a chunked iterator of rows from an SQLAlchemy select.

    This is particularly useful in combination with the streaming pager.

    The select should have a stable order, the offset and select may return same items multiple times.
    Any limit or offset already set on the select is overridden.
    """
    offset = 0
    while True:
        chunk = list(sql_session.execute(query.offset(offset).limit(chunk_size)))
        yield from chunk
        if len(chunk) < chunk_size:
            return
        offset += chunk_size


def iter_in_chunks(
    sql_session: Session,
    query: Select[tuple[T]],
    chunk_size: int = DEFAULT_STREAMING_ITER_CHUNK_SIZE,
) -> Iterator[T]:
    """
    `iter_rows_in_chunks`, but yields the first column only.
    """
    return (row[0] for row in iter_rows_in_chunks(sql_session, query, chunk_size))


def iter_in_keyset_chunks(
    sql_session: Session,
    query: Select[tuple[T]],
    keys: Sequence[InstrumentedAttribute[Any]],
    descending: bool = False,
    chunk_size: int = DEFAULT_STREAMING_ITER_CHUNK_SIZE,
) -> Iterator[T]:
    """
    `iter_in_chunks`, but each chunk continues after the last item of the previous chunk
    instead of skipping past an offset.

    This is generally more efficient than using an offset,
    see https://use-the-index-luke.com/no-offset

    - The select must yield ORM entities with `keys` as attributes
    - The select will be ordered by `keys`, overriding any order already set on it
    - The order must be total
    """

    query = (
        query.order_by(None)
        .order_by(*[key.desc() if descending else key.asc() for key in keys])
        .offset(None)
        .limit(chunk_size)
    )

    position = tuple_(*keys)
    last: tuple[Any, ...] | None = None
    while True:
        chunk_query = query
        if last is not None:
            chunk_query = query.where(
                position < tuple_(*last) if descending else position > tuple_(*last),
            )
        chunk = list(sql_session.scalars(chunk_query))
        yield from chunk
        if len(chunk) < chunk_size:
            return
        last = tuple(getattr(chunk[-1], key.key) for key in keys)


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

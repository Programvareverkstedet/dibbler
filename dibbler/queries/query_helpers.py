from datetime import datetime
from typing import TypeVar

from sqlalchemy import (
    BindParameter,
    ColumnExpressionArgument,
    literal,
    select,
)
from sqlalchemy.orm import QueryableAttribute

from dibbler.models import Transaction

T = TypeVar("T")


def const(value: T) -> BindParameter[T]:
    """
    Create a constant SQL literal bind parameter.

    This is useful to avoid too many `?` bind parameters in SQL queries,
    when the input value is known to be safe.
    """

    return literal(value, literal_execute=True)


CONST_ZERO: BindParameter[int] = const(0)
"""A constant SQL expression `0`. This will render as a literal `0` in SQL queries."""

CONST_ONE: BindParameter[int] = const(1)
"""A constant SQL expression `1`. This will render as a literal `1` in SQL queries."""

CONST_TRUE: BindParameter[bool] = const(True)
"""A constant SQL expression `TRUE`. This will render as a literal `TRUE` in SQL queries."""

CONST_FALSE: BindParameter[bool] = const(False)
"""A constant SQL expression `FALSE`. This will render as a literal `FALSE` in SQL queries."""

CONST_NONE: BindParameter[None] = const(None)
"""A constant SQL expression `NULL`. This will render as a literal `NULL` in SQL queries."""


def until_filter(
    until_time: BindParameter[datetime] | None = None,
    until_transaction_id: BindParameter[int] | None = None,
    until_inclusive: bool = True,
    transaction_time: QueryableAttribute = Transaction.time,
) -> ColumnExpressionArgument[bool]:
    """
    Create a filter condition for transactions up to a given time or transaction.

    Only one of `until_time` or `until_transaction_id` may be specified.
    """

    assert not (until_time is not None and until_transaction_id is not None), (
        "Cannot filter by both until_time and until_transaction_id."
    )

    match (until_time, until_transaction_id, until_inclusive):
        case (BindParameter(), None, True):
            return transaction_time <= until_time
        case (BindParameter(), None, False):
            return transaction_time < until_time
        case (None, BindParameter(), True):
            return (
                transaction_time
                <= select(Transaction.time)
                .where(Transaction.id == until_transaction_id)
                .scalar_subquery()
            )
        case (None, BindParameter(), False):
            return (
                transaction_time
                < select(Transaction.time)
                .where(Transaction.id == until_transaction_id)
                .scalar_subquery()
            )

    return CONST_TRUE


def after_filter(
    after_time: BindParameter[datetime] | None = None,
    after_transaction_id: BindParameter[int] | None = None,
    after_inclusive: bool = True,
    transaction_time: QueryableAttribute = Transaction.time,
) -> ColumnExpressionArgument[bool]:
    """
    Create a filter condition for transactions after a given time or transaction.

    Only one of `after_time` or `after_transaction_id` may be specified.
    """

    assert not (after_time is not None and after_transaction_id is not None), (
        "Cannot filter by both after_time and after_transaction_id."
    )

    match (after_time, after_transaction_id, after_inclusive):
        case (BindParameter(), None, True):
            return transaction_time >= after_time
        case (BindParameter(), None, False):
            return transaction_time > after_time
        case (None, BindParameter(), True):
            return (
                transaction_time
                >= select(Transaction.time)
                .where(Transaction.id == after_transaction_id)
                .scalar_subquery()
            )
        case (None, BindParameter(), False):
            return (
                transaction_time
                > select(Transaction.time)
                .where(Transaction.id == after_transaction_id)
                .scalar_subquery()
            )

    return CONST_TRUE

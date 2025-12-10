from typing import TypeVar
from sqlalchemy import BindParameter, literal

T = TypeVar("T")

def const(value: T) -> BindParameter[T]:
    """
    Create a constant SQL literal bind parameter.

    This is useful to avoid too many `?` bind parameters in SQL queries,
    when the input value is known to be safe.
    """

    return literal(value, literal_execute=True)

CONST_ZERO: BindParameter[int] = const(0)
CONST_ONE: BindParameter[int] = const(1)
CONST_TRUE: BindParameter[bool] = const(True)
CONST_FALSE: BindParameter[bool] = const(False)
CONST_NONE: BindParameter[None] = const(None)

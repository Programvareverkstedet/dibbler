from collections.abc import Iterator, Mapping
from enum import Enum
from typing import TypeVar

from sqlalchemy import CheckConstraint, ColumnElement, and_, column, or_
from sqlalchemy.orm import Query

T = TypeVar("T")


def type_field_constraints(
    expected_fields: Mapping[Enum, Mapping[str, bool | None]],
    *,
    type_column: str = "type",
    name_prefix: str = "ck",
    treat_empty_as_forbidden: bool = False,
) -> list[CheckConstraint]:
    """
    Helper to create sql check constraints from a mapping of log item type to required/optional/forbidden fields.
    """

    def is_forbidden(field: str) -> ColumnElement[bool]:
        if treat_empty_as_forbidden:
            return or_(column(field).is_(None), column(field) == "")
        return column(field).is_(None)

    constraints = []
    for entry_type, fields in expected_fields.items():
        required = {field for field, state in fields.items() if state is True}
        forbidden = {field for field, state in fields.items() if state is False}
        if not required and not forbidden:
            continue
        constraints.append(
            CheckConstraint(
                or_(
                    column(type_column) != entry_type.value,
                    and_(
                        *(column(field).is_not(None) for field in required),
                        *(is_forbidden(field) for field in forbidden),
                    ),
                ),
                name=f"{name_prefix}_{entry_type.value}_fields",
            ),
        )

    return constraints


def iter_in_chunks(query: Query[T], chunk_size: int = 64) -> Iterator[T]:
    """
    Create a chunked iterator from an SQLAlchemy query.

    This is particularly useful in combination with the streaming pager.
    """
    offset = 0
    while True:
        chunk = query.offset(offset).limit(chunk_size).all()
        yield from chunk
        if len(chunk) < chunk_size:
            return
        offset += chunk_size

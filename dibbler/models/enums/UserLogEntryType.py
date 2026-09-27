from enum import StrEnum, auto

from sqlalchemy import Enum as SQLEnum


class UserLogEntryType(StrEnum):
    CREATE = auto()
    """A new user."""

    EDIT = auto()
    """An edit to an existing user."""

    DELETE = auto()
    """A deleted user."""


UserLogEntryTypeSQL = SQLEnum(
    UserLogEntryType,
    native_enum=True,
    create_constraint=True,
    validate_strings=True,
    values_callable=lambda x: [i.value for i in x],
)

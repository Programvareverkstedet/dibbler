from enum import StrEnum, auto

from sqlalchemy import Enum as SQLEnum


class TransactionLogEntryType(StrEnum):
    BUY_PRODUCT = auto()
    """Products bought by one or more buyers."""

    ADD_PRODUCT = auto()
    """Stock added, crediting one or more users."""

    ADJUST_STOCK = auto()
    """Correcting the product stock count for a single product."""

    TRANSFER = auto()
    """Credit moved between two users."""

    ADJUST_BALANCE = auto()
    """A manual credit adjustment for a single user."""


TransactionLogEntryTypeSQL = SQLEnum(
    TransactionLogEntryType,
    native_enum=True,
    create_constraint=True,
    validate_strings=True,
    values_callable=lambda x: [i.value for i in x],
)

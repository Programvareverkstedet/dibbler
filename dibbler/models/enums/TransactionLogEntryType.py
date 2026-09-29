from enum import StrEnum, auto
from typing import assert_never

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

    def display_name(self) -> str:
        """A human readable name of the entry type."""
        match self:
            case TransactionLogEntryType.BUY_PRODUCT:
                return "Buy"
            case TransactionLogEntryType.ADD_PRODUCT:
                return "Add Stock"
            case TransactionLogEntryType.ADJUST_STOCK:
                return "Adjust Stock"
            case TransactionLogEntryType.TRANSFER:
                return "Transfer"
            case TransactionLogEntryType.ADJUST_BALANCE:
                return "Adjust Balance"
            case _:
                assert_never(self)


TransactionLogEntryTypeSQL = SQLEnum(
    TransactionLogEntryType,
    native_enum=True,
    create_constraint=True,
    validate_strings=True,
    values_callable=lambda x: [i.value for i in x],
)

from enum import StrEnum, auto

from sqlalchemy import Enum as SQLEnum


class TransactionType(StrEnum):
    """
    Enum for transaction types.
    """

    ADD_PRODUCT = auto()
    ADJUST_BALANCE = auto()
    ADJUST_INTEREST = auto()
    ADJUST_PENALTY = auto()
    ADJUST_STOCK = auto()
    BUY_PRODUCT = auto()
    TRANSFER = auto()


TransactionTypeSQL = SQLEnum(
    TransactionType,
    native_enum=True,
    create_constraint=True,
    validate_strings=True,
    values_callable=lambda x: [i.value for i in x],
)

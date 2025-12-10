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
    JOINT = auto()
    JOINT_BUY_PRODUCT = auto()
    THROW_PRODUCT = auto()
    TRANSFER = auto()

    def as_literal_column(self):
        """
        Return the transaction type as a SQL literal column.

        This is useful to avoid too many `?` bind parameters in SQL queries,
        when the input value is known to be safe.
        """
        from sqlalchemy import literal_column

        return literal_column(f"'{self.value}'")


TransactionTypeSQL = SQLEnum(
    TransactionType,
    native_enum=True,
    create_constraint=True,
    validate_strings=True,
    values_callable=lambda x: [i.value for i in x],
)

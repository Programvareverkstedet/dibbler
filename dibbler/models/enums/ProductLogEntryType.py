from enum import StrEnum, auto

from sqlalchemy import Enum as SQLEnum


class ProductLogEntryType(StrEnum):
    CREATE = auto()
    """A new product."""

    EDIT = auto()
    """An edit to an existing product."""

    # TODO: add a `MERGE` type once merging products have been implemented.

    REMOVE_BARCODE = auto()
    """A barcode removed from an existing product."""

    # TODO: add a `MERGE` type once merging products have been implemented.

    DELETE = auto()
    """A deleted product."""


ProductLogEntryTypeSQL = SQLEnum(
    ProductLogEntryType,
    native_enum=True,
    create_constraint=True,
    validate_strings=True,
    values_callable=lambda x: [i.value for i in x],
)

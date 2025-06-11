from __future__ import annotations

from typing import Self

from sqlalchemy import (
    Boolean,
    Integer,
    String,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
)

from .Base import Base


class Product(Base):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    """Internal database ID"""

    bar_code: Mapped[str] = mapped_column(String(13), unique=True)
    """
        The bar code of the product.

        This is a unique identifier for the product, typically a 13-digit
        EAN-13 code.
    """

    name: Mapped[str] = mapped_column(String(45))
    """
        The name of the product.

        Please don't write fanfics here, this is not a place for that.
    """

    hidden: Mapped[bool] = mapped_column(Boolean, default=False)
    """
        Whether the product is hidden from the user interface.

        Hidden products are not shown in the product list, but can still be
        used in transactions.
    """

    def __init__(
        self: Self,
        bar_code: str,
        name: str,
        hidden: bool = False,
    ) -> None:
        self.bar_code = bar_code
        self.name = name
        self.hidden = hidden

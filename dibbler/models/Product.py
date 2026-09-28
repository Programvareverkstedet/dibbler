from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Integer,
    String,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from .Base import Base
from .mixins import UidMixin
from .ProductBarcode import ProductBarcode

if TYPE_CHECKING:
    from .PurchaseEntry import PurchaseEntry


class Product(Base, UidMixin):
    __tablename__ = "products"

    bar_code_length = 13
    name_length = 45

    name: Mapped[str] = mapped_column(String(name_length))
    price: Mapped[int] = mapped_column(Integer)
    stock: Mapped[int] = mapped_column(Integer)
    hidden: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    purchases: Mapped[set[PurchaseEntry]] = relationship(back_populates="product")
    barcodes: Mapped[set[ProductBarcode]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
    )

    bar_code_re = r"[0-9]+"
    name_re = r".+"

    def __init__(
        self,
        bar_code: str,
        name: str,
        price: int,
        stock: int = 0,
        hidden: bool = False,
    ) -> None:
        self.name = name
        self.barcodes = {ProductBarcode(code=bar_code)}
        self.price = price
        self.stock = stock
        self.hidden = hidden

    def __str__(self) -> str:
        return self.name

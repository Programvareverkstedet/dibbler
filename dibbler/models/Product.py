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

if TYPE_CHECKING:
    from .PurchaseEntry import PurchaseEntry
    from .UserProducts import UserProducts


class Product(Base):
    __tablename__ = "products"

    product_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    bar_code: Mapped[str] = mapped_column(String(13))
    name: Mapped[str] = mapped_column(String(45))
    price: Mapped[int] = mapped_column(Integer)
    stock: Mapped[int] = mapped_column(Integer)
    hidden: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    purchases: Mapped[set[PurchaseEntry]] = relationship(back_populates="product")
    users: Mapped[set[UserProducts]] = relationship(back_populates="product")

    bar_code_re = r"[0-9]+"
    name_re = r".+"
    name_length = 45

    def __init__(
        self,
        bar_code: str,
        name: str,
        price: int,
        stock: int = 0,
        hidden: bool = False,
    ):
        self.name = name
        self.bar_code = bar_code
        self.price = price
        self.stock = stock
        self.hidden = hidden

    def __str__(self) -> str:
        return self.name

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import (
    ForeignKey,
    Integer,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from dibbler.models.mixins import UidMixin

from .Base import Base

if TYPE_CHECKING:
    from .Product import Product
    from .Purchase import Purchase


class PurchaseEntry(Base, UidMixin):
    __tablename__ = "purchase_entries"

    amount: Mapped[int] = mapped_column(Integer)

    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"))
    purchase_id: Mapped[int] = mapped_column(ForeignKey("purchases.id"))

    product: Mapped[Product] = relationship(back_populates="purchases", lazy="joined")
    purchase: Mapped[Purchase] = relationship(back_populates="entries", lazy="joined")

    def __init__(
        self,
        purchase: Purchase,
        product: Product,
        amount: int,
    ) -> None:
        self.product = product
        self.purchase = purchase
        self.amount = amount

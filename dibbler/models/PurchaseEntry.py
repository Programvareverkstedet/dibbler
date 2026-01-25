from __future__ import annotations
from typing import TYPE_CHECKING

from sqlalchemy import (
    Integer,
    ForeignKey,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from .Base import Base

if TYPE_CHECKING:
    from .Product import Product
    from .Purchase import Purchase


class PurchaseEntry(Base):
    __tablename__ = "purchase_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    amount: Mapped[int] = mapped_column(Integer)

    product_id: Mapped[int] = mapped_column(ForeignKey("products.product_id"))
    purchase_id: Mapped[int] = mapped_column(ForeignKey("purchases.id"))

    product: Mapped[Product] = relationship(back_populates='purchases', lazy="joined")
    purchase: Mapped[Purchase] = relationship(back_populates='entries', lazy="joined")

    def __init__(self, purchase, product, amount):
        self.product = product
        self.product_bar_code = product.bar_code
        self.purchase = purchase
        self.amount = amount

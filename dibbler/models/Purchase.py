from __future__ import annotations
from typing import TYPE_CHECKING

from datetime import datetime
import math

from sqlalchemy import (
    DateTime,
    Integer,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from .Base import Base
from .Transaction import Transaction

if TYPE_CHECKING:
    from .PurchaseEntry import PurchaseEntry


class Purchase(Base):
    __tablename__ = "purchases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    time: Mapped[datetime] = mapped_column(DateTime)
    price: Mapped[int] = mapped_column(Integer)

    transactions: Mapped[set[Transaction]] = relationship(
        back_populates="purchase", order_by="Transaction.user_name"
    )
    entries: Mapped[set[PurchaseEntry]] = relationship(back_populates="purchase")

    def __init__(self):
        pass

    def is_complete(self) -> bool:
        return len(self.transactions) > 0 and len(self.entries) > 0

    def price_per_transaction(self, round_up: bool = True) -> int:
        if round_up:
            return int(math.ceil(float(self.price) / len(self.transactions)))
        else:
            return int(math.floor(float(self.price) / len(self.transactions)))

    def set_price(self, round_up: bool = True) -> None:
        self.price = 0
        for entry in self.entries:
            self.price += entry.amount * entry.product.price
        if len(self.transactions) > 0:
            for t in self.transactions:
                t.amount = self.price_per_transaction(round_up=round_up)

    def perform_purchase(self, ignore_penalty: bool = False, round_up: bool = True) -> None:
        self.time = datetime.now()
        self.set_price(round_up=round_up)
        for t in self.transactions:
            t.perform_transaction(ignore_penalty=ignore_penalty)
        for entry in self.entries:
            entry.product.stock -= entry.amount

    def perform_soft_purchase(self, price: int, round_up: bool = True) -> None:
        self.time = datetime.now()
        self.price = price
        for t in self.transactions:
            t.amount = self.price_per_transaction(round_up=round_up)
        for t in self.transactions:
            t.perform_transaction()

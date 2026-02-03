from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    ForeignKey,
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
    from .Purchase import Purchase
    from .User import User


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    time: Mapped[datetime] = mapped_column(DateTime)
    amount: Mapped[int] = mapped_column(Integer)
    penalty: Mapped[int] = mapped_column(Integer)
    description: Mapped[str | None] = mapped_column(String(50))

    user_name: Mapped[str] = mapped_column(ForeignKey("users.name"))
    purchase_id: Mapped[int | None] = mapped_column(ForeignKey("purchases.id"))

    user: Mapped[User] = relationship(lazy="joined")
    purchase: Mapped[Purchase] = relationship(back_populates="transactions", lazy="joined")

    def __init__(
        self,
        user: User,
        amount: int = 0,
        description: str | None = None,
        purchase: Purchase | None = None,
        penalty: int = 1,
    ):
        self.user = user
        self.amount = amount
        self.description = description
        self.purchase = purchase
        self.penalty = penalty

    def perform_transaction(self, ignore_penalty: bool = False) -> None:
        self.time = datetime.now()
        if not ignore_penalty:
            self.amount *= self.penalty
        self.user.credit -= self.amount

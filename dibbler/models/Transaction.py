from __future__ import annotations
from typing import TYPE_CHECKING

from datetime import datetime

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
    from .User import User
    from .Purchase import Purchase


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
    purchase: Mapped[Purchase] = relationship(lazy="joined")

    def __init__(self, user, amount=0, description=None, purchase=None, penalty=1):
        self.user = user
        self.amount = amount
        self.description = description
        self.purchase = purchase
        self.penalty = penalty

    def perform_transaction(self, ignore_penalty=False):
        self.time = datetime.datetime.now()
        if not ignore_penalty:
            self.amount *= self.penalty
        self.user.credit -= self.amount

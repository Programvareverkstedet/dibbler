from __future__ import annotations

from datetime import datetime  # noqa: TC003 SQLAlchemy needs this at runtime
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

from dibbler.models.mixins import UidMixin

from .Base import Base

if TYPE_CHECKING:
    from .Purchase import Purchase
    from .User import User


class Transaction(Base, UidMixin):
    __tablename__ = "transactions"

    description_length = 50

    time: Mapped[datetime] = mapped_column(DateTime)
    amount: Mapped[int] = mapped_column(Integer)
    penalty: Mapped[int] = mapped_column(Integer)
    description: Mapped[str | None] = mapped_column(String(description_length))

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
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
    ) -> None:
        self.user = user
        self.amount = amount
        self.description = description
        self.purchase = purchase
        self.penalty = penalty

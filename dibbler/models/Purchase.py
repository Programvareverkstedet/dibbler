from __future__ import annotations

from datetime import datetime  # noqa: TC003 SQLAlchemy needs this at runtime
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    Integer,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from dibbler.models.mixins import UidMixin

from .Base import Base
from .Transaction import Transaction

if TYPE_CHECKING:
    from .PurchaseEntry import PurchaseEntry


class Purchase(Base, UidMixin):
    __tablename__ = "purchases"

    time: Mapped[datetime] = mapped_column(DateTime)
    price: Mapped[int] = mapped_column(Integer)

    transactions: Mapped[set[Transaction]] = relationship(
        back_populates="purchase",
        order_by=Transaction.user_id,
    )
    entries: Mapped[set[PurchaseEntry]] = relationship(back_populates="purchase")

    def __init__(self) -> None:
        pass

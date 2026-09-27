from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    String,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from .Base import Base
from .enums import TransactionLogEntryType, TransactionLogEntryTypeSQL
from .mixins import UidMixin

if TYPE_CHECKING:
    from .xref_tables import TransactionLogProduct, TransactionLogUser


class TransactionLog(Base, UidMixin):
    __tablename__ = "transaction_log"

    time: Mapped[datetime] = mapped_column(DateTime)
    type: Mapped[TransactionLogEntryType] = mapped_column(TransactionLogEntryTypeSQL)
    description: Mapped[str | None] = mapped_column(String(50))

    products: Mapped[set[TransactionLogProduct]] = relationship(back_populates="transaction")
    users: Mapped[set[TransactionLogUser]] = relationship(back_populates="transaction")

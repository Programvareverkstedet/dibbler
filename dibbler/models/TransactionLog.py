from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    ForeignKey,
    String,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from dibbler.lib.sql_helpers import type_field_constraints

from .Base import Base
from .enums import TransactionLogEntryType, TransactionLogEntryTypeSQL
from .mixins import UidMixin

if TYPE_CHECKING:
    from .ProductLog import ProductLog
    from .xref_tables import TransactionLogProduct, TransactionLogUser


class TransactionLog(Base, UidMixin):
    __tablename__ = "transaction_log"
    __table_args__ = (
        *type_field_constraints(
            {
                TransactionLogEntryType.BUY_PRODUCT: {"merge_ref_id": False},
                TransactionLogEntryType.ADD_PRODUCT: {"merge_ref_id": False},
                TransactionLogEntryType.ADJUST_STOCK: {"merge_ref_id": None},
                TransactionLogEntryType.TRANSFER: {"merge_ref_id": False},
                TransactionLogEntryType.ADJUST_BALANCE: {"merge_ref_id": False},
            },
        ),
    )

    time: Mapped[datetime] = mapped_column(DateTime)
    type: Mapped[TransactionLogEntryType] = mapped_column(TransactionLogEntryTypeSQL)
    description: Mapped[str | None] = mapped_column(String(50))

    products: Mapped[set[TransactionLogProduct]] = relationship(back_populates="transaction")
    users: Mapped[set[TransactionLogUser]] = relationship(back_populates="transaction")

    merge_ref_id: Mapped[int | None] = mapped_column(ForeignKey("product_log.id"))
    merge_ref: Mapped[ProductLog | None] = relationship()

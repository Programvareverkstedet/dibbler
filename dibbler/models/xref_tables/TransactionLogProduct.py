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

from ..Base import Base
from ..mixins import UidMixin, XrefMixin

if TYPE_CHECKING:
    from ..Product import Product
    from ..TransactionLog import TransactionLog


class TransactionLogProduct(XrefMixin, Base, UidMixin):
    transaction_log_id: Mapped[int] = mapped_column(ForeignKey("transaction_log.id"))
    transaction: Mapped[TransactionLog] = relationship(back_populates="products")

    product_id: Mapped[int] = mapped_column(ForeignKey("products.product_id"))
    product: Mapped[Product] = relationship()

    amount: Mapped[int] = mapped_column(Integer)
    """How much stock added or removed."""

    price_at_time: Mapped[int] = mapped_column(Integer)
    """Snapshot of the product's price at the time."""

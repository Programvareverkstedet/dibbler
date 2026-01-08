from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from dibbler.models import Base

if TYPE_CHECKING:
    from dibbler.models import Transaction


class LastCacheTransaction(Base):
    """Tracks the last transaction that affected various caches."""

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    """Internal database ID"""

    transaction_id: Mapped[int | None] = mapped_column(ForeignKey("trx.id"), index=True)
    """The ID of the last transaction that affected the cache(s)."""

    transaction: Mapped[Transaction | None] = relationship(
        lazy="joined",
        foreign_keys=[transaction_id],
    )
    """The last transaction that affected the cache(s)."""

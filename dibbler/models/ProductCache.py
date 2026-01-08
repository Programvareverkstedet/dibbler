from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from dibbler.models import Base

if TYPE_CHECKING:
    from dibbler.models import LastCacheTransaction, Product


class ProductCache(Base):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    """Internal database ID"""

    product_id: Mapped[int] = mapped_column(ForeignKey("product.id"))
    product: Mapped[Product] = relationship(
        lazy="joined",
        foreign_keys=[product_id],
    )

    price: Mapped[int] = mapped_column(Integer)
    stock: Mapped[int] = mapped_column(Integer)

    last_cache_transaction_id: Mapped[int | None] = mapped_column(
        ForeignKey("last_cache_transaction.id"), nullable=True,
    )
    last_cache_transaction: Mapped[LastCacheTransaction | None] = relationship(
        lazy="joined",
        foreign_keys=[last_cache_transaction_id],
    )

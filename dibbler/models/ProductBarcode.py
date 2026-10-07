from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import (
    ForeignKey,
    String,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from .Base import Base
from .mixins import UidMixin

if TYPE_CHECKING:
    from .Product import Product


class ProductBarcode(Base, UidMixin):
    code: Mapped[str] = mapped_column(String(13), unique=True)

    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    product: Mapped[Product] = relationship(back_populates="barcodes")

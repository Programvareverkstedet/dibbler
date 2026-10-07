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

from ..Base import Base
from ..mixins import UidMixin, XrefMixin
from ..Product import Product

if TYPE_CHECKING:
    from ..ProductLog import ProductLog


class ProductMergedBarcode(XrefMixin, Base, UidMixin):
    """
    A barcode that was moved from the source to the target product of a merge.

    This is kept so that it is possible to undo merges in the future if needed.
    """

    merge_log_id: Mapped[int] = mapped_column(ForeignKey("product_log.id"), index=True)
    merge_log: Mapped[ProductLog] = relationship()

    # NOTE: Not a foreign key, the barcode might be removed from the product after the merge.
    barcode: Mapped[str] = mapped_column(String(Product.barcode_length))

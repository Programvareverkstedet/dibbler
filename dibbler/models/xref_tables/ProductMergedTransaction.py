from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from ..Base import Base
from ..mixins import UidMixin, XrefMixin

if TYPE_CHECKING:
    from ..ProductLog import ProductLog
    from .TransactionLogProduct import TransactionLogProduct


class ProductMergedTransaction(XrefMixin, Base, UidMixin):
    """
    A transaction entry that was moved from the source to the target product of a merge.

    This is kept so that it is possible to undo merges in the future if needed.
    """

    merge_log_id: Mapped[int] = mapped_column(ForeignKey("product_log.id"), index=True)
    merge_log: Mapped[ProductLog] = relationship()

    transaction_log_product_id: Mapped[int] = mapped_column(
        ForeignKey("xref_transaction_log_product.id"),
    )
    transaction_log_product: Mapped[TransactionLogProduct] = relationship()

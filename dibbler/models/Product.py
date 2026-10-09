from __future__ import annotations

from sqlalchemy import (
    Boolean,
    Integer,
    String,
    event,
    inspect,
)
from sqlalchemy.orm import (
    Mapped,
    Session,
    mapped_column,
    relationship,
)

from .Base import Base
from .mixins import UidMixin
from .ProductBarcode import ProductBarcode


class Product(Base, UidMixin):
    __tablename__ = "products"

    barcode_length = 13
    name_length = 45

    name: Mapped[str] = mapped_column(String(name_length))
    price: Mapped[int] = mapped_column(Integer)
    stock: Mapped[int] = mapped_column(Integer)
    hidden: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    barcodes: Mapped[set[ProductBarcode]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
    )

    barcode_re = r"[0-9]+"
    name_re = r".+"

    def __init__(
        self,
        barcode: str,
        name: str,
        price: int,
        stock: int = 0,
        hidden: bool = False,
    ) -> None:
        self.name = name
        self.barcodes = {ProductBarcode(code=barcode)}
        self.price = price
        self.stock = stock
        self.hidden = hidden

    def __str__(self) -> str:
        return self.name


@event.listens_for(Session, "before_flush")
def _validate_product_barcodes(
    session: Session,
    _flush_context: object,
    _instances: object,
) -> None:
    for product in (*session.new, *session.dirty):
        if not isinstance(product, Product) or product in session.deleted:
            continue

        # Skip checking the barcodes if the the session doesn't contain any history about it.
        barcodes_changed = inspect(product).attrs.barcodes.history.has_changes()
        if (product in session.new or barcodes_changed) and not product.barcodes:
            raise ValueError(f"Product {product.name!r} must have at least one barcode.")

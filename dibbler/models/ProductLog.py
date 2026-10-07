from __future__ import annotations

from datetime import datetime  # noqa: TC003 SQLAlchemy needs this at runtime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Integer,
    String,
    column,
    or_,
)
from sqlalchemy.orm import (
    Mapped,
    foreign,
    mapped_column,
    relationship,
)

from ._helpers import type_field_constraints
from .Base import Base
from .enums import ProductLogEntryType, ProductLogEntryTypeSQL
from .mixins import UidMixin
from .Product import Product


class ProductLog(Base, UidMixin):
    __tablename__ = "product_log"
    __table_args__ = (
        *type_field_constraints(
            {
                ProductLogEntryType.CREATE: {
                    "bar_code": False,
                    "name": True,
                    "price": True,
                    "hidden": True,
                    "merged_product_id": False,
                    "merge_ref_id": False,
                },
                ProductLogEntryType.DELETE: {
                    "bar_code": False,
                    "name": False,
                    "price": False,
                    "hidden": False,
                    "merged_product_id": False,
                    "merge_ref_id": None,
                },
                ProductLogEntryType.ADD_BARCODE: {
                    "bar_code": True,
                    "name": False,
                    "price": False,
                    "hidden": False,
                    "merged_product_id": False,
                    "merge_ref_id": False,
                },
                ProductLogEntryType.REMOVE_BARCODE: {
                    "bar_code": True,
                    "name": False,
                    "price": False,
                    "hidden": False,
                    "merged_product_id": False,
                    "merge_ref_id": False,
                },
                ProductLogEntryType.MERGE: {
                    "bar_code": False,
                    "name": False,
                    "price": False,
                    "hidden": False,
                    "merged_product_id": True,
                    "merge_ref_id": False,
                },
                ProductLogEntryType.EDIT: {
                    "bar_code": False,
                    "merged_product_id": False,
                    "merge_ref_id": None,
                },
            },
        ),
        CheckConstraint(
            or_(
                column("type") != ProductLogEntryType.EDIT.value,
                or_(
                    column("name").is_not(None),
                    column("price").is_not(None),
                    column("hidden").is_not(None),
                ),
            ),
            name="ck_edit_touches_something",
        ),
        CheckConstraint(
            or_(
                column("merge_ref_id").is_(None),
                column("merge_ref_id") != column("id"),
            ),
            name="ck_merge_ref_not_self",
        ),
    )

    time: Mapped[datetime] = mapped_column(DateTime)
    type: Mapped[ProductLogEntryType] = mapped_column(ProductLogEntryTypeSQL)

    # NOTE: Technically a foreign key, but we don't enforce so we can delete products.
    product_id: Mapped[int] = mapped_column(Integer, index=True)
    product: Mapped[Product | None] = relationship(
        primaryjoin=lambda: foreign(ProductLog.product_id) == Product.id,
        viewonly=True,
    )

    bar_code: Mapped[str | None] = mapped_column(String(Product.bar_code_length))
    name: Mapped[str | None] = mapped_column(String(Product.name_length))
    price: Mapped[int | None] = mapped_column(Integer)
    hidden: Mapped[bool | None] = mapped_column(Boolean)

    # NOTE: Technically a foreign key, but we don't enforce so we can delete products.
    merged_product_id: Mapped[int | None] = mapped_column(Integer)
    merged_product: Mapped[Product | None] = relationship(
        primaryjoin=lambda: foreign(ProductLog.merged_product_id) == Product.id,
        viewonly=True,
    )

    merge_ref_id: Mapped[int | None] = mapped_column(ForeignKey("product_log.id"))
    merge_ref: Mapped[ProductLog | None] = relationship(remote_side="ProductLog.id")

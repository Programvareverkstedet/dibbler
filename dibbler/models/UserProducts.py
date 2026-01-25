from __future__ import annotations
from typing import TYPE_CHECKING

from sqlalchemy import (
    Integer,
    ForeignKey,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from .Base import Base

if TYPE_CHECKING:
    from .User import User
    from .Product import Product


class UserProducts(Base):
    __tablename__ = "user_products"

    user_name: Mapped[str] = mapped_column(ForeignKey("users.name"), primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.product_id"), primary_key=True)

    count: Mapped[int] = mapped_column(Integer)
    sign: Mapped[int] = mapped_column(Integer)

    user: Mapped[User] = relationship(back_populates="products")
    product: Mapped[Product] = relationship(back_populates="users")

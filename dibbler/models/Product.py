from __future__ import annotations
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    Integer,
    String,
    func,
    select,
)
from sqlalchemy.orm import (
    Mapped,
    Session,
    mapped_column,
    relationship,
)

from .Base import Base
from .Transaction import Transaction
from .TransactionType import TransactionType
import dibbler.models.User as user

# if TYPE_CHECKING:
#     from .PurchaseEntry import PurchaseEntry
#     from .UserProducts import UserProducts


class Product(Base):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    bar_code: Mapped[str] = mapped_column(String(13))
    name: Mapped[str] = mapped_column(String(45))
    # price: Mapped[int] = mapped_column(Integer)
    # stock: Mapped[int] = mapped_column(Integer)
    hidden: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # - count (virtual)
    def stock(self, sql_session: Session) -> int:
        """
        Returns the number of products in stock.
        """

        added_products = sql_session.scalars(
            select(func.sum(Transaction.product_count))
            .where(
                Transaction.type == TransactionType.ADD_PRODUCT,
                Transaction.product_id == self.id,
            )
        ).one_or_none()

        bought_products = sql_session.scalars(
            select(func.sum(Transaction.product_count))
            .where(
                Transaction.type == TransactionType.BUY_PRODUCT,
                Transaction.product_id == self.id,
            )
        ).one_or_none()

        return (added_products or 0) - (bought_products or 0)

    def remaining_with_exact_price(self, sql_session: Session) -> list[int]:
      """
      Retrieves the remaining products with their exact price as they were bought.
      """

      stock = self.stock(sql_session)

      # TODO: only retrieve as many transactions as exists in the stock
      last_added = sql_session.scalars(
          select(Transaction)
          .where(
              Transaction.type == TransactionType.ADD_PRODUCT,
              Transaction.product_id == self.id,
          )
          .order_by(Transaction.time.desc())
      ).all()

      # result = []
      # while stock > 0 and last_added:

      ...

    def price(self, sql_session: Session) -> int:
        """
        Returns the price of the product.

        Average price over the last bought products.
        """

        remaining = self.remaining_with_exact_price(sql_session)

        if not remaining:
            return 0

        prices = [price for price in remaining]
        return sum(prices) // len(prices)

    def owned_by_user(self, sql_session: Session) -> dict[user.User, int]:
        """
        Returns an overview of how many of the remaining products are owned by which user.
        """

        ...

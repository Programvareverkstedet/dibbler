from __future__ import annotations

from typing import Self

from sqlalchemy import (
    Boolean,
    Integer,
    String,
    case,
    func,
    select,
)
from sqlalchemy.orm import (
    Mapped,
    Session,
    mapped_column,
)

import dibbler.models.User as user

from .Base import Base
from .Transaction import Transaction
from .TransactionType import TransactionType

# if TYPE_CHECKING:
#     from .PurchaseEntry import PurchaseEntry
#     from .UserProducts import UserProducts


class Product(Base):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    bar_code: Mapped[str] = mapped_column(String(13), unique=True)
    name: Mapped[str] = mapped_column(String(45))
    # price: Mapped[int] = mapped_column(Integer)
    # stock: Mapped[int] = mapped_column(Integer)
    hidden: Mapped[bool] = mapped_column(Boolean, default=False)

    def __init__(
        self: Self,
        bar_code: str,
        name: str,
        hidden: bool = False,
    ) -> None:
        self.bar_code = bar_code
        self.name = name
        self.hidden = hidden

    # - count (virtual)
    def stock(self: Self, sql_session: Session) -> int:
        """
        Returns the number of products in stock.
        """

        result = sql_session.scalars(
            select(
                func.sum(
                    case(
                        (
                            Transaction.type_ == TransactionType.ADD_PRODUCT,
                            Transaction.product_count,
                        ),
                        (
                            Transaction.type_ == TransactionType.BUY_PRODUCT,
                            -Transaction.product_count,
                        ),
                        (
                            Transaction.type_ == TransactionType.ADJUST_STOCK,
                            Transaction.product_count,
                        ),
                        else_=0,
                    )
                )
            ).where(
                Transaction.type_.in_(
                    [
                        TransactionType.BUY_PRODUCT,
                        TransactionType.ADD_PRODUCT,
                        TransactionType.ADJUST_STOCK,
                    ]
                ),
                Transaction.product_id == self.id,
            )
        ).one_or_none()

        return result or 0

    def remaining_with_exact_price(self: Self, sql_session: Session) -> list[int]:
        """
        Retrieves the remaining products with their exact price as they were bought.
        """

        stock = self.stock(sql_session)

        # TODO: only retrieve as many transactions as exists in the stock
        last_added = sql_session.scalars(
            select(
                func.row_number(),
                Transaction.time,
                Transaction.per_product,
                Transaction.product_count,
            )
            .where(
                Transaction.type_ == TransactionType.ADD_PRODUCT,
                Transaction.product_id == self.id,
            )
            .order_by(Transaction.time.desc())
        ).all()

        # result = []
        # while stock > 0 and last_added:

        ...

    def price(self: Self, sql_session: Session) -> int:
        """
        Returns the price of the product.

        Average price over the last bought products.
        """

        return Transaction.product_price(sql_session=sql_session, product=self)

    def owned_by_user(self: Self, sql_session: Session) -> dict[user.User, int]:
        """
        Returns an overview of how many of the remaining products are owned by which user.
        """

        ...

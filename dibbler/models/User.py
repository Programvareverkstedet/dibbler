from __future__ import annotations

from typing import Self

from sqlalchemy import (
    Integer,
    String,
    func,
    select,
)
from sqlalchemy.orm import (
    Mapped,
    Session,
    mapped_column,
)

import dibbler.models.Product as product

from .Base import Base
from .Transaction import Transaction
from .TransactionType import TransactionType


class User(Base):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    name: Mapped[str] = mapped_column(String(20), unique=True)
    card: Mapped[str | None] = mapped_column(String(20))
    rfid: Mapped[str | None] = mapped_column(String(20))

    # name_re = r"[a-z]+"
    # card_re = r"(([Nn][Tt][Nn][Uu])?[0-9]+)?"
    # rfid_re = r"[0-9a-fA-F]*"

    def __init__(self: Self, name: str, card: str | None = None, rfid: str | None = None) -> None:
        self.name = name
        self.card = card
        self.rfid = rfid

    # def __str__(self):
    #     return self.name

    # def is_anonymous(self):
    #     return self.card == "11122233"

    def credit(self, sql_session: Session) -> int:
        """
        Returns the current credit of the user.
        """

        balance_adjustments = (
            select(func.coalesce(func.sum(Transaction.amount).label("balance_adjustments"), 0))
            .where(
                Transaction.user_id == self.id,
                Transaction.type == TransactionType.ADJUST_BALANCE,
            )
            .scalar_subquery()
        )

        transfers_to_other_users = (
            select(func.coalesce(func.sum(Transaction.amount).label("transfers_to_other_users"), 0))
            .where(
                Transaction.user_id == self.id,
                Transaction.type == TransactionType.TRANSFER,
                Transaction.transfer_user_id != self.id,
            )
            .scalar_subquery()
        )

        transfers_to_self = (
            select(func.coalesce(func.sum(Transaction.amount).label("transfers_to_self"), 0))
            .where(
                Transaction.transfer_user_id == self.id,
                Transaction.type == TransactionType.TRANSFER,
                Transaction.user_id != self.id,
            )
            .scalar_subquery()
        )

        add_products = (
            select(func.coalesce(func.sum(Transaction.amount).label("add_products"), 0))
            .where(
                Transaction.user_id == self.id,
                Transaction.type == TransactionType.ADD_PRODUCT,
            )
            .scalar_subquery()
        )

        buy_products = (
            select(func.coalesce(func.sum(Transaction.amount).label("buy_products"), 0))
            .where(
                Transaction.user_id == self.id,
                Transaction.type == TransactionType.BUY_PRODUCT,
            )
            .scalar_subquery()
        )

        result = sql_session.scalar(
            select(
                # TODO: clearly define and fix the sign of the amount
                (
                    0
                    + balance_adjustments
                    - transfers_to_other_users
                    + transfers_to_self
                    + add_products
                    - buy_products
                ).label("credit")
            )
        )

        assert result is not None, "Credit calculation returned None, please file a bug report."

        return result

    def products(self, sql_session: Session) -> list[tuple[product.Product, int]]:
        """
        Returns the products that the user has put into the system (and has not been purchased yet)
        """

        ...

    def transactions(self, sql_session: Session) -> list[Transaction]:
        """
        Returns the transactions of the user.
        """

        return list(
            sql_session.scalars(
                select(Transaction)
                .where(Transaction.user_id == self.id)
                .order_by(Transaction.time.desc())
            ).all()
        )

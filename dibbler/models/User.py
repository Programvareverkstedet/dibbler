from __future__ import annotations
from typing import TYPE_CHECKING

from sqlalchemy import (
    func,
    select,
    column,
    Integer,
    String,
)
from sqlalchemy.orm import (
    Session,
    Mapped,
    mapped_column,
    relationship,
)

from .Base import Base
from .TransactionType import TransactionType
from .Transaction import Transaction

import dibbler.models.Product as product


class User(Base):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    name: Mapped[str] = mapped_column(String(20), unique=True)
    card: Mapped[str | None] = mapped_column(String(20))
    rfid: Mapped[str | None] = mapped_column(String(20))

    def credit(self, sql_session: Session) -> int:
        """
        Returns the current credit of the user.
        """

        result = sql_session.scalars(
            select(
              # TODO: clearly define and fix the sign of the amount
              - column("transfers_to_other_users")
              + column("transfers_to_self")
              + column("add_products")
              - column("buy_products")
            ).select_from(
                select(
                    func.sum(Transaction.amount)
                    .label("transfers_to_other_users")
                    .where(
                        Transaction.user_id == self.id,
                        Transaction.type == TransactionType.TRANSFER,
                        Transaction.transfer_user_id != self.id,
                    )
                )
                .subquery(),
                select(
                    func.sum(Transaction.amount)
                    .label("transfers_to_self")
                    .where(
                        Transaction.transfer_user_id == self.id,
                        Transaction.type == TransactionType.TRANSFER,
                        Transaction.user_id != self.id,
                    )
                )
                .subquery(),
                select(
                    func.sum(Transaction.amount)
                    .label("add_products")
                    .where(
                        Transaction.user_id == self.id,
                        Transaction.type == TransactionType.ADD_PRODUCT,
                    )
                )
                .subquery(),
                select(
                    func.sum(Transaction.amount)
                    .label("buy_products")
                    .where(
                        Transaction.user_id == self.id,
                        Transaction.type == TransactionType.BUY_PRODUCT,
                    )
                ).subquery(),
            )
        ).one_or_none()

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

        return list(sql_session.scalars(
            select(Transaction)
            .where(Transaction.user_id == self.id)
            .order_by(
                Transaction.time.desc()
            )
        ).all())

    # name_re = r"[a-z]+"
    # card_re = r"(([Nn][Tt][Nn][Uu])?[0-9]+)?"
    # rfid_re = r"[0-9a-fA-F]*"

    # def __init__(self, name, card, rfid=None, credit=0):
    #     self.name = name
    #     if card == "":
    #         card = None
    #     self.card = card
    #     if rfid == "":
    #         rfid = None
    #     self.rfid = rfid
    #     self.credit = credit

    # def __str__(self):
    #     return self.name

    # def is_anonymous(self):
    #     return self.card == "11122233"

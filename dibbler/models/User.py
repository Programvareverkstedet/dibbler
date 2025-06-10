from __future__ import annotations

from typing import Self

from sqlalchemy import (
    Integer,
    String,
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

    # TODO: rename to 'balance' everywhere
    def credit(self, sql_session: Session) -> int:
        """
        Returns the current credit of the user.
        """

        result = Transaction.user_balance(
            sql_session=sql_session,
            user=self,
        )

        return result

    def products(self, sql_session: Session) -> list[tuple[product.Product, int]]:
        """
        Returns the products that the user has put into the system (and has not been purchased yet)
        """

        ...

    def transactions(self, sql_session: Session) -> list[Transaction]:
        """
        Returns the transactions of the user in chronological order.
        """

        return list(
            sql_session.scalars(
                select(Transaction)
                .where(Transaction.user_id == self.id)
                .order_by(Transaction.time.asc())
            ).all()
        )

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import (
    Integer,
    String,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from .Base import Base

if TYPE_CHECKING:
    from .Transaction import Transaction
    from .UserProducts import UserProducts


class User(Base):
    __tablename__ = "users"
    name: Mapped[str] = mapped_column(String(10), primary_key=True)
    credit: Mapped[int] = mapped_column(Integer)
    card: Mapped[str | None] = mapped_column(String(20))
    rfid: Mapped[str | None] = mapped_column(String(20))

    products: Mapped[list[UserProducts]] = relationship(back_populates="user")
    transactions: Mapped[list[Transaction]] = relationship(
        back_populates="user",
        order_by="Transaction.time",
    )

    name_re = r"[a-z]+"
    card_re = r"(([Nn][Tt][Nn][Uu])?[0-9]+)?"
    rfid_re = r"[0-9a-fA-F]*"

    def __init__(
        self,
        name: str,
        card: str | None,
        rfid: str | None = None,
        credit: int = 0,
    ) -> None:
        self.name = name
        if card == "":
            card = None
        self.card = card
        if rfid == "":
            rfid = None
        self.rfid = rfid
        self.credit = credit

    def __str__(self) -> str:
        return self.name

    def is_anonymous(self) -> bool:
        return self.card == "11122233"

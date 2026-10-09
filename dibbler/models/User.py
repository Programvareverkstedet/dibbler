from __future__ import annotations

from sqlalchemy import (
    Integer,
    String,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
)

from .Base import Base
from .mixins import UidMixin


class User(Base, UidMixin):
    __tablename__ = "users"

    name_length = 10
    card_length = 20
    rfid_length = 20

    name: Mapped[str] = mapped_column(String(name_length), unique=True, index=True)
    credit: Mapped[int] = mapped_column(Integer)
    card: Mapped[str | None] = mapped_column(String(card_length), unique=True)
    rfid: Mapped[str | None] = mapped_column(String(rfid_length), unique=True)

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

from __future__ import annotations

from typing import Self

from sqlalchemy import (
    Integer,
    String,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
)

from .Base import Base


class User(Base):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    """Internal database ID"""

    name: Mapped[str] = mapped_column(String(20), unique=True)
    """The PVV username of the user."""

    card: Mapped[str | None] = mapped_column(String(20))
    """The NTNU card number of the user."""

    rfid: Mapped[str | None] = mapped_column(String(20))
    """The RFID tag of the user (if they have any, rare these days)."""

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

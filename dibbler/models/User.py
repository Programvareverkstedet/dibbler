from __future__ import annotations

from typing import TYPE_CHECKING, Self

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

from .Base import Base

if TYPE_CHECKING:
    from .Transaction import Transaction


class User(Base):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    """Internal database ID"""

    name: Mapped[str] = mapped_column(String(20), unique=True)
    """
        The PVV username of the user.
    """

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

    # TODO: move to 'queries'
    def transactions(self, sql_session: Session) -> list[Transaction]:
        """
        Returns the transactions of the user in chronological order.
        """

        from .Transaction import Transaction  # Import here to avoid circular import

        return list(
            sql_session.scalars(
                select(Transaction)
                .where(Transaction.user_id == self.id)
                .order_by(Transaction.time.asc())
            ).all()
        )

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import (
    ForeignKey,
    Integer,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from ..Base import Base
from ..mixins import UidMixin, XrefMixin

if TYPE_CHECKING:
    from ..TransactionLog import TransactionLog
    from ..User import User


class TransactionLogUser(XrefMixin, Base, UidMixin):
    transaction_log_id: Mapped[int] = mapped_column(ForeignKey("transaction_log.id"))
    transaction: Mapped[TransactionLog] = relationship(back_populates="users")

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    user: Mapped[User] = relationship()

    amount: Mapped[int] = mapped_column(Integer)
    """How much credit added or removed. Penalty is already applied."""

    penalty: Mapped[int | None] = mapped_column(Integer)
    """Multiplier that was applied to the amount."""

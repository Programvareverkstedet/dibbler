from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from dibbler.models import Base

if TYPE_CHECKING:
    from dibbler.models import LastCacheTransaction, User


# More like user balance cash money flow, amirite?
class UserCache(Base):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    """internal database id"""

    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))
    user: Mapped[User] = relationship(
        lazy="joined",
        foreign_keys=[user_id],
    )

    balance: Mapped[int] = mapped_column(Integer)

    last_cache_transaction_id: Mapped[int | None] = mapped_column(
        ForeignKey("last_cache_transaction.id"), nullable=True,
    )
    last_cache_transaction: Mapped[LastCacheTransaction | None] = relationship(
        lazy="joined",
        foreign_keys=[last_cache_transaction_id],
    )

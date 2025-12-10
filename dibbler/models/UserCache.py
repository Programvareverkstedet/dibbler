from datetime import datetime

from sqlalchemy import Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from dibbler.models import Base


# More like user balance cash money flow, amirite?
class UserBalanceCache(Base):
    user_id: Mapped[int] = mapped_column(Integer, primary_key=True)

    balance: Mapped[int] = mapped_column(Integer)
    timestamp: Mapped[datetime] = mapped_column(DateTime)

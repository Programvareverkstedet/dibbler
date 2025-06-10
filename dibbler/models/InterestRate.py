from datetime import datetime

from sqlalchemy import Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from dibbler.models import Base

class InterestRate(Base):
    timestamp: Mapped[datetime] = mapped_column(DateTime)
    percentage: Mapped[int] = mapped_column(Integer)

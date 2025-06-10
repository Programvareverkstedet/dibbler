from datetime import datetime

from sqlalchemy import Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from dibbler.models import Base

class ProductPriceCache(Base):
    product_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime)
    price: Mapped[int] = mapped_column(Integer)

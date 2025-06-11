from datetime import datetime

from sqlalchemy import Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from dibbler.models import Base

class ProductCache(Base):
    product_id: Mapped[int] = mapped_column(Integer, primary_key=True)

    price: Mapped[int] = mapped_column(Integer)
    price_timestamp: Mapped[datetime] = mapped_column(DateTime)

    stock: Mapped[int] = mapped_column(Integer)
    stock_timestamp: Mapped[datetime] = mapped_column(DateTime)

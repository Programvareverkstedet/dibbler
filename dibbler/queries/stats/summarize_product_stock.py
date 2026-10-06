from typing import NamedTuple

from sqlalchemy import select
from sqlalchemy.orm import Session

from dibbler.models import Product

from .._helpers import count_where, sum_where


class ProductStockSummary(NamedTuple):
    positive_stock_count: int
    """Number of products with a positive stock level."""

    zero_stock_count: int
    """Number of products with a zero stock level."""

    negative_stock_count: int
    """Number of products with a negative stock level."""

    in_stock_value: int
    """Total value of products with a positive stock level."""

    negative_stock_value: int
    """Total value of products with a negative stock level."""

    @property
    def product_count(self) -> int:
        """Total number of products, including those with zero stock."""
        return self.positive_stock_count + self.zero_stock_count + self.negative_stock_count

    @property
    def out_of_stock_count(self) -> int:
        """Number of products with a zero or negative stock level."""
        return self.zero_stock_count + self.negative_stock_count

    @property
    def stock_value(self) -> int:
        """Total value of all products, including those with zero stock."""
        return self.in_stock_value + self.negative_stock_value


def summarize_product_stock(
    sql_session: Session,
    include_hidden: bool = False,
) -> ProductStockSummary:
    query = select(
        count_where(Product.stock > 0),
        count_where(Product.stock == 0),
        count_where(Product.stock < 0),
        sum_where(Product.stock > 0, Product.price * Product.stock),
        sum_where(Product.stock < 0, Product.price * Product.stock),
    )

    if not include_hidden:
        query = query.where(Product.hidden.is_(False))

    return ProductStockSummary(*sql_session.execute(query).one())

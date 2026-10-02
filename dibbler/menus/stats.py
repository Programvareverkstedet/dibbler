from collections.abc import Iterator

from sqlalchemy.orm import Session

from dibbler.lib.pager import pager, streaming_pager
from dibbler.lib.sql_helpers import iter_rows_in_chunks
from dibbler.lib.statistikkHelpers import statisticsTextOnly
from dibbler.models import Product
from dibbler.queries.stats import (
    list_products_top_selling_query,
    summarize_product_stock,
    summarize_user_balance,
)

from .helpermenus import Menu

__all__ = [
    "ProductPopularityMenu",
    "ProductRevenueMenu",
    "BalanceMenu",
    "LoggedStatisticsMenu",
]


class ProductPopularityMenu(Menu):
    def __init__(self, sql_session: Session) -> None:
        super().__init__("Products by popularity", sql_session)

    def _execute(self, **_kwargs) -> None:
        self.print_header()

        def lines() -> Iterator[str]:
            line_format = "%10s | %s\n"
            yield line_format % ("items sold", "product")
            yield "-" * (13 + Product.name_length) + "\n"
            rows = iter_rows_in_chunks(self.sql_session, list_products_top_selling_query())
            for product, sold_amount, _sold_credit in rows:
                yield line_format % (sold_amount, product.name)

        streaming_pager(lines())


class ProductRevenueMenu(Menu):
    def __init__(self, sql_session: Session) -> None:
        super().__init__("Products by revenue", sql_session)

    def _execute(self, **_kwargs) -> None:
        self.print_header()

        def lines() -> Iterator[str]:
            line_format = "%7s | %10s | %s\n"
            yield line_format % ("revenue", "items sold", "product")
            yield "-" * (23 + Product.name_length) + "\n"
            query = list_products_top_selling_query(rank_by_credit=True)
            for product, sold_amount, sold_credit in iter_rows_in_chunks(self.sql_session, query):
                yield line_format % (sold_credit, sold_amount, product.name)

        streaming_pager(lines())


class BalanceMenu(Menu):
    def __init__(self, sql_session: Session) -> None:
        super().__init__("Total balance of PVVVV", sql_session)

    def _execute(self, **_kwargs) -> None:
        self.print_header()
        stock = summarize_product_stock(self.sql_session, include_hidden=True)
        balance = summarize_user_balance(self.sql_session)

        line_format = "%15s | %5d \n"
        text = line_format % ("Total value", stock.in_stock_value)
        text += 24 * "-" + "\n"
        text += line_format % ("Positive credit", balance.positive_balance)
        text += line_format % ("Negative credit", balance.negative_balance)
        text += line_format % ("Total credit", balance.total)
        text += 24 * "-" + "\n"
        text += line_format % ("Total balance", stock.in_stock_value - balance.total)
        pager(text)


class LoggedStatisticsMenu(Menu):
    def __init__(self, sql_session: Session) -> None:
        super().__init__("Statistics from log", sql_session)

    def _execute(self, **_kwargs) -> None:
        statisticsTextOnly(self.sql_session)

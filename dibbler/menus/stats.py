from collections.abc import Iterator

from sqlalchemy.orm import Session

from dibbler.lib.pager import pager, streaming_pager
from dibbler.lib.sql_helpers import iter_rows_in_chunks
from dibbler.lib.statistikkHelpers import statisticsTextOnly
from dibbler.models import Product
from dibbler.queries.stats import list_products_top_selling_query

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
        text = ""
        total_value = 0
        product_list = self.sql_session.query(Product).filter(Product.stock > 0).all()
        for p in product_list:
            total_value += p.stock * p.price

        total_positive_credit = (
            self.sql_session.query(func.coalesce(func.sum(User.credit), 0))
            .filter(User.credit > 0)
            .first()[0]
        )
        total_negative_credit = (
            self.sql_session.query(func.coalesce(func.sum(User.credit), 0))
            .filter(User.credit < 0)
            .first()[0]
        )

        total_credit = total_positive_credit + total_negative_credit
        total_balance = total_value - total_credit

        line_format = "%15s | %5d \n"
        text += line_format % ("Total value", total_value)
        text += 24 * "-" + "\n"
        text += line_format % ("Positive credit", total_positive_credit)
        text += line_format % ("Negative credit", total_negative_credit)
        text += line_format % ("Total credit", total_credit)
        text += 24 * "-" + "\n"
        text += line_format % ("Total balance", total_balance)
        pager(text)


class LoggedStatisticsMenu(Menu):
    def __init__(self, sql_session: Session) -> None:
        super().__init__("Statistics from log", sql_session)

    def _execute(self, **_kwargs) -> None:
        statisticsTextOnly(self.sql_session)

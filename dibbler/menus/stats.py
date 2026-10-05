from collections.abc import Callable

from sqlalchemy import Select
from sqlalchemy.orm import Session

from dibbler.lib.pager import streaming_pager
from dibbler.lib.sql_helpers import iter_rows_in_chunks
from dibbler.lib.tables import Table, TableColumn
from dibbler.models import Product, User
from dibbler.queries.stats import (
    list_products_top_selling_query,
    list_users_top_depositing_query,
    list_users_top_restocking_query,
    list_users_top_spending_query,
    list_users_top_withdrawing_query,
    summarize_product_stock,
    summarize_user_balance,
)

from .helpermenus import Menu

__all__ = [
    "BalanceMenu",
    "ProductPopularityMenu",
    "ProductRevenueMenu",
    "UsersByDepositsMenu",
    "UsersByRestockingMenu",
    "UsersBySpendingMenu",
    "UsersByWithdrawalsMenu",
]


class ProductPopularityMenu(Menu):
    def __init__(self, sql_session: Session) -> None:
        super().__init__("Products by popularity", sql_session)

    def _execute(self, **_kwargs) -> None:
        self.print_header()
        table = Table(
            TableColumn("items sold", 10, align="right"),
            TableColumn("product", Product.name_length),
        )
        rows = iter_rows_in_chunks(self.sql_session, list_products_top_selling_query())
        streaming_pager(
            table.render((sold_amount, product.name) for product, sold_amount, _ in rows),
        )


class ProductRevenueMenu(Menu):
    def __init__(self, sql_session: Session) -> None:
        super().__init__("Products by revenue", sql_session)

    def _execute(self, **_kwargs) -> None:
        self.print_header()
        table = Table(
            TableColumn("revenue", 7, align="right"),
            TableColumn("items sold", 10, align="right"),
            TableColumn("product", Product.name_length),
        )
        query = list_products_top_selling_query(rank_by_credit=True)
        rows = iter_rows_in_chunks(self.sql_session, query)
        streaming_pager(
            table.render(
                (sold_credit, sold_amount, product.name)
                for product, sold_amount, sold_credit in rows
            ),
        )


class BalanceMenu(Menu):
    def __init__(self, sql_session: Session) -> None:
        super().__init__("Total balance of PVVVV", sql_session)

    def _execute(self, **_kwargs) -> None:
        self.print_header()
        stock = summarize_product_stock(self.sql_session, include_hidden=True)
        balance = summarize_user_balance(self.sql_session)

        table = Table(TableColumn("", 15, align="right"), TableColumn("", 5, align="right"))
        text = table.row("Total value", stock.in_stock_value)
        text += table.hline()
        text += table.row("Positive credit", balance.positive_balance)
        text += table.row("Negative credit", balance.negative_balance)
        text += table.row("Total credit", balance.total)
        text += table.hline()
        text += table.row("Total balance", stock.in_stock_value - balance.total)
        print(text)
        self.pause()


class _UserRankingMenu(Menu):
    def __init__(
        self,
        name: str,
        sql_session: Session,
        query: Callable[
            [],
            Select[tuple[User, int]],
        ],
        credit_header: str,
    ) -> None:
        super().__init__(name, sql_session)
        self.query = query
        self.credit_header = credit_header

    def _execute(self, **_kwargs) -> None:
        self.print_header()
        table = Table(
            TableColumn(self.credit_header, 10, align="right"),
            TableColumn("user", User.name_length),
        )
        rows = iter_rows_in_chunks(self.sql_session, self.query())
        streaming_pager(table.render((credit, user.name) for user, credit in rows))


class UsersBySpendingMenu(_UserRankingMenu):
    def __init__(self, sql_session: Session) -> None:
        super().__init__("Users by spending", sql_session, list_users_top_spending_query, "spent")


class UsersByRestockingMenu(_UserRankingMenu):
    def __init__(self, sql_session: Session) -> None:
        super().__init__(
            "Users by restocking",
            sql_session,
            list_users_top_restocking_query,
            "received",
        )


class UsersByDepositsMenu(_UserRankingMenu):
    def __init__(self, sql_session: Session) -> None:
        super().__init__(
            "Users by deposits",
            sql_session,
            list_users_top_depositing_query,
            "deposited",
        )


class UsersByWithdrawalsMenu(_UserRankingMenu):
    def __init__(self, sql_session: Session) -> None:
        super().__init__(
            "Users by withdrawals",
            sql_session,
            list_users_top_withdrawing_query,
            "withdrawn",
        )

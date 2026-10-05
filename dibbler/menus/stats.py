from collections.abc import Callable, Iterator

from sqlalchemy.orm import Session

from dibbler.lib.pager import streaming_pager
from dibbler.lib.tables import Table, TableColumn
from dibbler.models import Product, User
from dibbler.queries.stats import (
    UserCredit,
    products_top_selling_stream,
    summarize_product_stock,
    summarize_user_balance,
    users_top_depositing_stream,
    users_top_restocking_stream,
    users_top_spending_stream,
    users_top_withdrawing_stream,
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
        sales = products_top_selling_stream(self.sql_session)
        streaming_pager(table.render((s.sold_amount, s.product.name) for s in sales))


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
        sales = products_top_selling_stream(self.sql_session, rank_by_credit=True)
        streaming_pager(
            table.render((s.sold_credit, s.sold_amount, s.product.name) for s in sales),
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
        stream_ranking: Callable[
            [Session],
            Iterator[UserCredit],
        ],
        credit_header: str,
    ) -> None:
        super().__init__(name, sql_session)
        self.stream_ranking = stream_ranking
        self.credit_header = credit_header

    def _execute(self, **_kwargs) -> None:
        self.print_header()
        table = Table(
            TableColumn(self.credit_header, 10, align="right"),
            TableColumn("user", User.name_length),
        )
        ranking = self.stream_ranking(self.sql_session)
        streaming_pager(table.render((u.credit, u.user.name) for u in ranking))


class UsersBySpendingMenu(_UserRankingMenu):
    def __init__(self, sql_session: Session) -> None:
        super().__init__("Users by spending", sql_session, users_top_spending_stream, "spent")


class UsersByRestockingMenu(_UserRankingMenu):
    def __init__(self, sql_session: Session) -> None:
        super().__init__(
            "Users by restocking",
            sql_session,
            users_top_restocking_stream,
            "received",
        )


class UsersByDepositsMenu(_UserRankingMenu):
    def __init__(self, sql_session: Session) -> None:
        super().__init__(
            "Users by deposits",
            sql_session,
            users_top_depositing_stream,
            "deposited",
        )


class UsersByWithdrawalsMenu(_UserRankingMenu):
    def __init__(self, sql_session: Session) -> None:
        super().__init__(
            "Users by withdrawals",
            sql_session,
            users_top_withdrawing_stream,
            "withdrawn",
        )

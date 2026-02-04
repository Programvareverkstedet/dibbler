from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from dibbler.lib.helpers import less
from dibbler.lib.statistikkHelpers import statisticsTextOnly
from dibbler.models import Product, PurchaseEntry, User

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
        text = ""
        sub = (
            self.sql_session.query(
                PurchaseEntry.product_id,
                func.sum(PurchaseEntry.amount).label("purchase_count"),
            )
            .filter(PurchaseEntry.amount > 0)
            .group_by(PurchaseEntry.product_id)
            .subquery()
        )
        product_list = (
            self.sql_session.query(Product, sub.c.purchase_count)
            .outerjoin(sub, Product.product_id == sub.c.product_id)
            .order_by(desc(sub.c.purchase_count))
            .filter(sub.c.purchase_count is not None)
            .all()
        )
        line_format = "{0:10s} | {1:>45s}\n"
        text += line_format.format("items sold", "product")
        text += "-" * (31 + Product.name_length) + "\n"
        for product, number in product_list:
            if number is None:
                continue
            text += line_format.format(str(number), product.name)
        less(text)


class ProductRevenueMenu(Menu):
    def __init__(self, sql_session: Session) -> None:
        super().__init__("Products by revenue", sql_session)

    def _execute(self, **_kwargs) -> None:
        self.print_header()
        text = ""
        sub = (
            self.sql_session.query(
                PurchaseEntry.product_id,
                func.sum(PurchaseEntry.amount).label("purchase_count"),
            )
            .filter(PurchaseEntry.amount > 0)
            .group_by(PurchaseEntry.product_id)
            .subquery()
        )
        product_list = (
            self.sql_session.query(Product, sub.c.purchase_count)
            .outerjoin(sub, Product.product_id == sub.c.product_id)
            .order_by(desc(sub.c.purchase_count * Product.price))
            .filter(sub.c.purchase_count is not None)
            .all()
        )
        line_format = "{0:7s} | {1:10s} | {2:6s} | {3:>45s}\n"
        text += line_format.format("revenue", "items sold", "price", "product")
        text += "-" * (31 + Product.name_length) + "\n"
        for product, number in product_list:
            if number is None:
                continue
            text += line_format.format(
                str(number * product.price),
                str(number),
                str(product.price),
                product.name,
            )
        less(text)


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
        less(text)


class LoggedStatisticsMenu(Menu):
    def __init__(self, sql_session: Session) -> None:
        super().__init__("Statistics from log", sql_session)

    def _execute(self, **_kwargs) -> None:
        statisticsTextOnly(self.sql_session)

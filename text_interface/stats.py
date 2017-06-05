import sqlalchemy
from db import PurchaseEntry, Product, User
from helpers import less
from sqlalchemy import desc
from sqlalchemy import func
from statistikkHelpers import statisticsTextOnly
from text_interface.helpermenus import Menu

__all__ = ["ProductPopularityMenu", "ProductRevenueMenu", "BalanceMenu", "LoggedStatisticsMenu"]


class ProductPopularityMenu(Menu):
    def __init__(self):
        Menu.__init__(self, 'Products by popularity', uses_db=True)

    def _execute(self):
        self.print_header()
        text = ''
        sub = \
            self.session.query(PurchaseEntry.product_id,
                               func.count('*').label('purchase_count')) \
                .group_by(PurchaseEntry.product_id) \
                .subquery()
        product_list = \
            self.session.query(Product, sub.c.purchase_count) \
                .outerjoin((sub, Product.product_id == sub.c.product_id)) \
                .order_by(desc(sub.c.purchase_count)) \
                .filter(sub.c.purchase_count is not None) \
                .all()
        line_format = '%10s | %-' + str(Product.name_length) + 's\n'
        text += line_format % ('items sold', 'product')
        text += '-' * 58 + '\n'
        for product, number in product_list:
            text += line_format % (number, product.name)
        less(text)


class ProductRevenueMenu(Menu):
    def __init__(self):
        Menu.__init__(self, 'Products by revenue', uses_db=True)

    def _execute(self):
        self.print_header()
        text = ''
        sub = \
            self.session.query(PurchaseEntry.product_id,
                               func.count('*').label('purchase_count')) \
                .group_by(PurchaseEntry.product_id) \
                .subquery()
        product_list = \
            self.session.query(Product, sub.c.purchase_count) \
                .outerjoin((sub, Product.product_id == sub.c.product_id)) \
                .order_by(desc(sub.c.purchase_count * Product.price)) \
                .filter(sub.c.purchase_count is not None) \
                .all()
        line_format = '%7s | %10s | %5s | %-' + str(Product.name_length) + 's\n'
        text += line_format % ('revenue', 'items sold', 'price', 'product')
        text += '-' * (31 + Product.name_length) + '\n'
        for product, number in product_list:
            text += line_format % (number * product.price, number, product.price, product.name)
        less(text)


class BalanceMenu(Menu):
    def __init__(self):
        Menu.__init__(self, 'Total balance of PVVVV', uses_db=True)

    def _execute(self):
        self.print_header()
        text = ''
        total_value = 0
        product_list = self.session.query(Product).filter(Product.stock > 0).all()
        for p in product_list:
            total_value += p.stock * p.price

        total_credit = self.session.query(sqlalchemy.func.sum(User.credit)).first()[0]
        total_balance = total_value - total_credit

        line_format = '%15s | %5d \n'
        text += line_format % ('Total value', total_value)
        text += 24 * '-' + '\n'
        text += line_format % ('Total credit', total_credit)
        text += 24 * '-' + '\n'
        text += line_format % ('Total balance', total_balance)
        less(text)


class LoggedStatisticsMenu(Menu):
    def __init__(self):
        Menu.__init__(self, 'Statistics from log', uses_db=True)

    def _execute(self):
        statisticsTextOnly()



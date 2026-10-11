from collections.abc import Iterator
from datetime import datetime
from itertools import chain

from sqlalchemy.orm import Session

from dibbler.lib.pager import streaming_pager
from dibbler.lib.render_transaction_log import render_transaction_log
from dibbler.lib.tables import BORDER_WIDTH, MAX_SCREEN_SIZE, SEPARATOR, Table, TableColumn
from dibbler.models import TransactionLog, User
from dibbler.queries import (
    adjust_balance,
    product_info,
    product_list_info_stream,
    transaction_log_stream,
    transfer,
    user_info,
    user_list_info_stream,
    user_product_stats_stream,
)
from dibbler.queries.adjust_balance import MAX_BALANCE_ADJUSTMENT

from .editing import EditProductMenu, EditUserMenu
from .helpermenus import Menu, Selector


def _format_last_activity(last_activity: datetime | None) -> str:
    if last_activity is not None:
        return f"{last_activity:%Y-%m-%d %H:%M:%S}"
    return "never"


def _page_transaction_log(entries: Iterator[TransactionLog]) -> None:
    first = next(entries, None)
    if first is None:
        print("No transactions yet")
        return

    streaming_pager(render_transaction_log(chain([first], entries)))


class TransferMenu(Menu):
    def __init__(self, sql_session: Session) -> None:
        super().__init__("Transfer credit between users", sql_session)

    def _execute(self, **_kwargs) -> None:
        self.print_header()
        amount = self.input_int("Transfer amount", 1, 100000)
        self.set_context(f"Transferring {amount:d} kr", display=False)
        user1 = self.input_user("From user")
        self.add_to_context(f" from {user1.name}")
        user2 = self.input_user("To user")
        self.add_to_context(f" to {user2.name}")
        comment = self.input_str("Comment")
        assert comment is not None
        self.add_to_context(f" (comment) {user2.name}")

        try:
            transfer(self.sql_session, user1, user2, amount, comment=comment)
            self.sql_session.commit()
            print(f"Transferred {amount:d} kr from {user1} to {user2}")
            print(f"User {user1}'s credit is now {user1.credit:d} kr")
            print(f"User {user2}'s credit is now {user2.credit:d} kr")
            print(f"Comment: {comment}")
        except Exception as e:
            self.rollback_and_report(
                e,
                "Could not perform transfer",
                "Could not transfer %d kr from %r to %r",
                amount,
                user1.name,
                user2.name,
            )
            self.pause()


class ShowUserMenu(Menu):
    def __init__(self, sql_session: Session) -> None:
        super().__init__("Show user", sql_session)

    def _execute(self, **_kwargs) -> None:
        self.print_header()
        user = self.input_user("User name, card number or RFID")
        print(f"User name: {user.name}")
        print(f"Card number: {user.card}")
        print(f"RFID: {user.rfid}")
        print(f"Credit: {user.credit} kr")
        info = user_info(self.sql_session, user)
        print(f"Last activity: {_format_last_activity(info.last_activity)}")
        print(f"Products bought: {info.products_bought}")
        print(f"Products added: {info.products_added}")
        print(f"Stock adjustments: {info.stock_adjustments}")
        print(
            f"Balance adjustments: {info.balance_adjustments} "
            f"(net {info.balance_adjustment_sum:+} kr)",
        )
        selector = Selector(
            f"What do you want to know about {user.name}?",
            self.sql_session,
            items=[
                ("transactions", "Transactions"),
                ("products", f"Which products {user.name} has bought, and how many"),
                ("edit", f"Edit {user.name}"),
            ],
        )
        what = selector.execute()
        if what == "transactions":
            self.print_transactions(user)
        elif what == "products":
            self.print_product_stats(user)
        elif what == "edit":
            EditUserMenu(self.sql_session).execute(user=user)
        else:
            print("What what?")

    def print_transactions(self, user: User) -> None:
        _page_transaction_log(
            transaction_log_stream(self.sql_session, user=user, newest_first=True),
        )

    def print_product_stats(self, user: User) -> None:
        stats = user_product_stats_stream(self.sql_session, user=user)
        first = next(stats, None)
        if first is None:
            print("No products bought or added yet")
            return

        count_width = len("bought")
        name_width = MAX_SCREEN_SIZE - BORDER_WIDTH - 2 * (count_width + len(SEPARATOR))
        table = Table(
            TableColumn("product", name_width),
            TableColumn("bought", count_width, align="right"),
            TableColumn("added", count_width, align="right"),
        )
        streaming_pager(
            table.render(
                ((s.product.name, s.bought, s.added) for s in chain([first], stats)),
                hline=False,
            ),
        )


class UserListMenu(Menu):
    def __init__(self, sql_session: Session) -> None:
        super().__init__("User list", sql_session)

    def _execute(self, **_kwargs) -> None:
        self.print_header()

        table = Table(
            TableColumn("username", 12),
            TableColumn("credit", 6, align="right"),
            TableColumn("bought", 6, align="right"),
            TableColumn("added", 6, align="right"),
            TableColumn("last activity", 19),
        )

        total_credit = 0

        def rows() -> Iterator[tuple[object, ...]]:
            nonlocal total_credit
            for info in user_list_info_stream(self.sql_session):
                total_credit += info.user.credit
                yield (
                    info.user.name,
                    info.user.credit,
                    info.products_bought,
                    info.products_added,
                    _format_last_activity(info.last_activity),
                )

        streaming_pager(
            table.render(
                rows(),
                footer=lambda: ("total credit", total_credit, "", "", ""),
            ),
        )


class AdjustCreditMenu(Menu):
    def __init__(self, sql_session: Session) -> None:
        super().__init__("Adjust credit", sql_session)

    def _execute(self, **_kwargs) -> None:
        self.print_header()
        user = self.input_user("User")
        print(f"User {user.name}'s credit is {user.credit:d} kr")
        self.set_context(f"Adjusting credit for user {user.name}", display=False)
        print("(Note on sign convention: Enter a positive amount here if you have")
        print("added money to the PVVVV money box, a negative amount if you have")
        print("taken money from it)")
        amount = self.input_int("Add amount", -MAX_BALANCE_ADJUSTMENT, MAX_BALANCE_ADJUSTMENT)
        print('(The "log message" will show up in the transaction history in the')
        print('"Show user" menu.  It is not necessary to enter a message, but it')
        print("might be useful to help you remember why you adjusted the credit)")
        description = self.input_str(
            "Log message",
            length_range=(0, TransactionLog.description_length),
        )
        if description == "":
            description = "manually adjusted credit"
        try:
            adjust_balance(self.sql_session, user, -amount, description=description)
            self.sql_session.commit()
            print(f"User {user.name}'s credit is now {user.credit:d} kr")
        except Exception as e:
            self.rollback_and_report(
                e,
                "Could not store transaction",
                "Could not adjust credit of %r by %d kr",
                user.name,
                amount,
            )
            self.pause()


class ProductListMenu(Menu):
    def __init__(self, sql_session: Session) -> None:
        super().__init__("Product list", sql_session)

    def _execute(self, **_kwargs) -> None:
        self.print_header()
        table = Table(
            TableColumn("barcode", 20),
            TableColumn("price", 5, align="right"),
            TableColumn("name", 36),
            TableColumn("stock", 5, align="right"),
        )

        total_value = 0

        def rows() -> Iterator[tuple[object, ...]]:
            nonlocal total_value
            for info in product_list_info_stream(self.sql_session):
                p = info.product
                total_value += p.price * p.stock
                codes = sorted(bc.code for bc in p.barcodes)
                extra = len(codes) - 1
                barcode_summary = codes[0] if extra == 0 else f"{codes[0]} (+{extra})"
                yield (barcode_summary, p.price, p.name, p.stock)

        streaming_pager(
            table.render(
                rows(),
                footer=lambda: ("Total value", total_value, "", ""),
            ),
        )


class ProductSearchMenu(Menu):
    def __init__(self, sql_session: Session) -> None:
        super().__init__("Product search", sql_session)

    def _execute(self, **_kwargs) -> None:
        self.print_header()
        self.set_context("Enter (part of) product name or barcode")
        product = self.input_product()
        print(
            ", ".join(
                [
                    f"Result: {product.name}",
                    f"price: {product.price} kr",
                    f"stock: {product.stock}",
                    f"hidden: {'Y' if product.hidden else 'N'}",
                ],
            ),
        )
        print("barcodes:")
        for code in sorted(bc.code for bc in product.barcodes):
            print(f"  - {code}")
        info = product_info(self.sql_session, product)
        print(f"Last activity: {_format_last_activity(info.last_activity)}")
        print(f"Times bought: {info.times_bought}")
        print(f"Times added: {info.times_added}")
        print(f"Stock adjustments: {info.stock_adjustments} (net {info.stock_adjustment_sum:+})")
        selector = Selector(
            f"What do you want to know about {product.name}?",
            self.sql_session,
            items=[
                ("transactions", "Transactions"),
                ("edit", f"Edit {product.name}"),
            ],
        )
        what = selector.execute()
        if what == "transactions":
            _page_transaction_log(
                transaction_log_stream(self.sql_session, product=product, newest_first=True),
            )
        elif what == "edit":
            EditProductMenu(self.sql_session).execute(product=product)
        else:
            print("What what?")


class TransactionLogMenu(Menu):
    def __init__(self, sql_session: Session) -> None:
        super().__init__("Transaction log", sql_session)

    def _execute(self, **_kwargs) -> None:
        self.print_header()
        _page_transaction_log(transaction_log_stream(self.sql_session, newest_first=True))

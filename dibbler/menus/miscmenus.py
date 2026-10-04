from collections.abc import Iterator
from datetime import datetime
from itertools import chain

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from dibbler.lib.pager import streaming_pager
from dibbler.lib.render_transaction_log import render_transaction_log
from dibbler.lib.sql_helpers import iter_in_chunks, iter_rows_in_chunks
from dibbler.lib.syslog import get_syslog_logger
from dibbler.models import Product, TransactionLog, User
from dibbler.queries import (
    adjust_balance,
    product_info,
    transaction_log_query,
    transfer,
    user_info,
    user_list_info_query,
    user_product_stats_query,
)

from .helpermenus import Menu, Selector

logger = get_syslog_logger()

MAX_SCREEN_SIZE = 80


def _format_last_activity(last_activity: datetime | None) -> str:
    if last_activity is not None:
        return f"{last_activity:%Y-%m-%d %H:%M:%S}"
    return "never"


def _page_transaction_log(sql_session: Session, query: Select[tuple[TransactionLog]]) -> None:
    entries = iter_in_chunks(sql_session, query)
    first = next(entries, None)
    if first is None:
        print("No transactions yet")
        return

    streaming_pager(render_transaction_log(chain([first], entries), ascii_only=True))


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
        except ValueError as e:
            self.sql_session.rollback()
            print(f"Could not perform transfer: {e}")
        except Exception as e:
            logger.error(
                "Could not transfer %d kr from %r to %r",
                amount,
                user1.name,
                user2.name,
                exc_info=e,
            )
            self.sql_session.rollback()
            print(f"Could not perform transfer: {e}")
            # self.pause()


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
            ],
        )
        what = selector.execute()
        if what == "transactions":
            self.print_transactions(user)
        elif what == "products":
            self.print_product_stats(user)
        else:
            print("What what?")

    def print_transactions(self, user: User) -> None:
        _page_transaction_log(
            self.sql_session,
            transaction_log_query(user=user, newest_first=True),
        )

    def print_product_stats(self, user: User) -> None:
        query = user_product_stats_query(user=user)
        rows = iter_rows_in_chunks(self.sql_session, query)
        first = next(rows, None)
        if first is None:
            print("No products bought or added yet")
            return

        count_width = len("bought")
        name_width = MAX_SCREEN_SIZE - 2 * (count_width + 1)

        def line(
            name: str,
            bought: int | str,
            added: int | str,
        ) -> str:
            return f"{name[:name_width]:<{name_width}} {bought:>{count_width}} {added:>{count_width}}\n"

        def lines() -> Iterator[str]:
            yield line("product", "bought", "added")
            for product, bought, added in chain([first], rows):
                yield line(product.name, bought, added)

        streaming_pager(lines())


class UserListMenu(Menu):
    def __init__(self, sql_session: Session) -> None:
        super().__init__("User list", sql_session)

    def _execute(self, **_kwargs) -> None:
        self.print_header()

        def lines() -> Iterator[str]:
            line_format = "%-12s | %6s | %6s | %6s | %-19s\n"
            header = line_format % ("username", "credit", "bought", "added", "last activity")
            hline = "-" * (len(header) - 1) + "\n"
            yield header
            yield hline
            total_credit = 0
            rows = iter_rows_in_chunks(self.sql_session, user_list_info_query())
            for user, bought, added, last_activity in rows:
                total_credit += user.credit
                yield line_format % (
                    user.name,
                    user.credit,
                    bought,
                    added,
                    _format_last_activity(last_activity),
                )
            yield hline
            yield (line_format % ("total credit", total_credit, "", "", "")).rstrip() + "\n"

        streaming_pager(lines())


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
        amount = self.input_int("Add amount", -100000, 100000)
        print('(The "log message" will show up in the transaction history in the')
        print('"Show user" menu.  It is not necessary to enter a message, but it')
        print("might be useful to help you remember why you adjusted the credit)")
        description = self.input_str("Log message", length_range=(0, 50))
        if description == "":
            description = "manually adjusted credit"
        try:
            adjust_balance(self.sql_session, user, -amount, description=description)
            self.sql_session.commit()
            print(f"User {user.name}'s credit is now {user.credit:d} kr")
        except ValueError as e:
            self.sql_session.rollback()
            print(f"Could not store transaction: {e}")
        except Exception as e:
            logger.error(
                "Could not adjust credit of %r by %d kr",
                user.name,
                amount,
                exc_info=e,
            )
            self.sql_session.rollback()
            print(f"Could not store transaction: {e}")
            # self.pause()


class ProductListMenu(Menu):
    def __init__(self, sql_session: Session) -> None:
        super().__init__("Product list", sql_session)

    def _execute(self, **_kwargs) -> None:
        self.print_header()
        name_width = 40
        line_format = f"%-20s | %5s | %-{name_width}s | %5s \n"

        def lines() -> Iterator[str]:
            yield line_format % ("bar code", "price", "name", "stock")
            yield MAX_SCREEN_SIZE * "-" + "\n"
            total_value = 0
            product_list = (
                select(Product)
                .where(Product.hidden.is_(False))
                .order_by(Product.stock.desc(), Product.id)
            )
            for p in iter_in_chunks(self.sql_session, product_list):
                total_value += p.price * p.stock
                codes = sorted(bc.code for bc in p.barcodes)
                extra = len(codes) - 1
                barcode_summary = codes[0] if extra == 0 else f"{codes[0]} (+{extra})"
                yield line_format % (
                    barcode_summary,
                    p.price,
                    p.name[:name_width],
                    p.stock,
                )
            yield MAX_SCREEN_SIZE * "-" + "\n"
            yield line_format % (
                "Total value",
                total_value,
                "",
                "",
            )

        streaming_pager(lines())


class ProductSearchMenu(Menu):
    def __init__(self, sql_session: Session) -> None:
        super().__init__("Product search", sql_session)

    def _execute(self, **_kwargs) -> None:
        self.print_header()
        self.set_context("Enter (part of) product name or bar code")
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
            ],
        )
        what = selector.execute()
        if what == "transactions":
            _page_transaction_log(
                self.sql_session,
                transaction_log_query(product=product, newest_first=True),
            )
        else:
            print("What what?")


class TransactionLogMenu(Menu):
    def __init__(self, sql_session: Session) -> None:
        super().__init__("Transaction log", sql_session)

    def _execute(self, **_kwargs) -> None:
        self.print_header()
        _page_transaction_log(
            self.sql_session,
            transaction_log_query(newest_first=True),
        )

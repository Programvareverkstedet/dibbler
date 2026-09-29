from collections.abc import Iterator

from sqlalchemy import select
from sqlalchemy.orm import Session

from dibbler.conf import config
from dibbler.lib.pager import pager, streaming_pager
from dibbler.lib.render_transaction_log import render_transaction_log
from dibbler.lib.sql_helpers import iter_in_chunks
from dibbler.models import Product, User
from dibbler.queries import adjust_balance, transaction_log_query, transfer

from .helpermenus import Menu, Selector

MAX_SCREEN_SIZE = 80


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
        selector = Selector(
            f"What do you want to know about {user.name}?",
            self.sql_session,
            items=[
                (
                    "transactions",
                    "Recent transactions (List of last "
                    + str(config["limits"]["user_recent_transaction_limit"])
                    + ")",
                ),
                ("products", f"Which products {user.name} has bought, and how many"),
                ("transactions-all", "Everything (List of all transactions)"),
            ],
        )
        what = selector.execute()
        if what == "transactions":
            self.print_transactions(user, config["limits"]["user_recent_transaction_limit"])
        elif what == "products":
            self.print_purchased_products(user)
        elif what == "transactions-all":
            self.print_transactions(user)
        else:
            print("What what?")

    @staticmethod
    def print_transactions(user: User, limit: int | None = None) -> None:
        num_trans = len(user.transactions)
        if limit is None:
            limit = num_trans
        if num_trans <= limit:
            string = f"{user.name}'s transactions ({num_trans:d}):\n"
        else:
            string = f"{user.name}'s transactions ({num_trans:d}, showing only last {limit:d}):\n"
        for t in user.transactions[-1 : -limit - 1 : -1]:
            string += f" * {t.time.isoformat(' ')}: {'in' if t.amount < 0 else 'out'} {abs(t.amount)} kr, "
            if t.purchase:
                products = []
                for entry in t.purchase.entries:
                    amount = f"{abs(entry.amount)}x " if abs(entry.amount) != 1 else ""
                    product = f"{amount}{entry.product.name}"
                    products.append(product)
                string += "purchase ("
                string += ", ".join(products)
                string += ")"
                if t.penalty > 1:
                    string += f" * {t.penalty:d}x penalty applied"
            elif t.description is not None:
                string += t.description
            string += "\n"
        pager(string)

    @staticmethod
    def print_purchased_products(user: User) -> None:
        products = []
        for ref in user.products:
            product = ref.product
            count = ref.count
            if count > 0:
                products.append((product, count))
        num_products = len(products)
        if num_products == 0:
            print("No products purchased yet")
        else:
            text = ""
            text += "Products purchased:\n"
            for product, count in products:
                text += f"{product.name:<47} {count:>3}\n"
            pager(text)


class UserListMenu(Menu):
    def __init__(self, sql_session: Session) -> None:
        super().__init__("User list", sql_session)

    def _execute(self, **_kwargs) -> None:
        self.print_header()

        def lines() -> Iterator[str]:
            line_format = "%-12s | %6s\n"
            hline = "---------------------\n"
            yield line_format % ("username", "credit")
            yield hline
            total_credit = 0
            users = select(User).order_by(User.id)
            for user in iter_in_chunks(self.sql_session, users):
                total_credit += user.credit
                yield line_format % (user.name, user.credit)
            yield hline
            yield line_format % ("total credit", total_credit)

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
        except Exception as e:
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
        # self.pause()


class TransactionLogMenu(Menu):
    def __init__(self, sql_session: Session) -> None:
        super().__init__("Transaction log", sql_session)

    def _execute(self, **_kwargs) -> None:
        self.print_header()

        query = transaction_log_query(newest_first=True)
        entries = iter_in_chunks(self.sql_session, query)
        streaming_pager(render_transaction_log(entries, ascii_only=True))

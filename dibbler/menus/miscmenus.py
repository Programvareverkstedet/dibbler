import sqlalchemy
from sqlalchemy.orm import Session

from dibbler.conf import config
from dibbler.lib.helpers import less
from dibbler.models import Product, Transaction, User

from .helpermenus import Menu, Selector


class TransferMenu(Menu):
    def __init__(self, sql_session: Session):
        super().__init__("Transfer credit between users", sql_session)

    def _execute(self):
        self.print_header()
        amount = self.input_int("Transfer amount", 1, 100000)
        self.set_context(f"Transferring {amount:d} kr", display=False)
        user1 = self.input_user("From user")
        self.add_to_context(f" from {user1.name}")
        user2 = self.input_user("To user")
        self.add_to_context(f" to {user2.name}")
        comment = self.input_str("Comment")
        self.add_to_context(f" (comment) {user2.name}")

        t1 = Transaction(user1, amount, f'transfer to {user2.name} "{comment}"')
        t2 = Transaction(user2, -amount, f'transfer from {user1.name} "{comment}"')
        t1.perform_transaction()
        t2.perform_transaction()
        self.sql_session.add(t1)
        self.sql_session.add(t2)
        try:
            self.sql_session.commit()
            print(f"Transferred {amount:d} kr from {user1} to {user2}")
            print(f"User {user1}'s credit is now {user1.credit:d} kr")
            print(f"User {user2}'s credit is now {user2.credit:d} kr")
            print(f"Comment: {comment}")
        except sqlalchemy.exc.SQLAlchemyError as e:
            self.sql_session.rollback()
            print(f"Could not perform transfer: {e}")
            # self.pause()


class ShowUserMenu(Menu):
    def __init__(self, sql_session: Session):
        super().__init__("Show user", sql_session)

    def _execute(self):
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
        less(string)

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
            less(text)


class UserListMenu(Menu):
    def __init__(self, sql_session: Session):
        super().__init__("User list", sql_session)

    def _execute(self):
        self.print_header()
        user_list = self.sql_session.query(User).all()
        total_credit = self.sql_session.query(sqlalchemy.func.sum(User.credit)).first()[0]

        line_format = "%-12s | %6s\n"
        hline = "---------------------\n"
        text = ""
        text += line_format % ("username", "credit")
        text += hline
        for user in user_list:
            text += line_format % (user.name, user.credit)
        text += hline
        text += line_format % ("total credit", total_credit)
        less(text)


class AdjustCreditMenu(Menu):
    def __init__(self, sql_session: Session):
        super().__init__("Adjust credit", sql_session)

    def _execute(self):
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
        transaction = Transaction(user, -amount, description)
        transaction.perform_transaction()
        self.sql_session.add(transaction)
        try:
            self.sql_session.commit()
            print(f"User {user.name}'s credit is now {user.credit:d} kr")
        except sqlalchemy.exc.SQLAlchemyError as e:
            self.sql_session.rollback()
            print(f"Could not store transaction: {e}")
            # self.pause()


class ProductListMenu(Menu):
    def __init__(self, sql_session: Session):
        super().__init__("Product list", sql_session)

    def _execute(self):
        self.print_header()
        text = ""
        product_list = (
            self.sql_session.query(Product)
            .filter(Product.hidden.is_(False))
            .order_by(Product.stock.desc())
        )
        total_value = 0
        for p in product_list:
            total_value += p.price * p.stock
        line_format = "%-15s | %5s | %-" + str(Product.name_length) + "s | %5s \n"
        text += line_format % ("bar code", "price", "name", "stock")
        text += 78 * "-" + "\n"
        for p in product_list:
            text += line_format % (p.bar_code, p.price, p.name, p.stock)
        text += 78 * "-" + "\n"
        text += line_format % (
            "Total value",
            total_value,
            "",
            "",
        )
        less(text)


class ProductSearchMenu(Menu):
    def __init__(self, sql_session: Session):
        super().__init__("Product search", sql_session)

    def _execute(self):
        self.print_header()
        self.set_context("Enter (part of) product name or bar code")
        product = self.input_product()
        print(
            ", ".join(
                [
                    f"Result: {product.name}",
                    f"price: {product.price} kr",
                    f"bar code: {product.bar_code}",
                    f"stock: {product.stock}",
                    f"hidden: {'Y' if product.hidden else 'N'}",
                ]
            )
        )
        # self.pause()

from math import ceil

import sqlalchemy
from sqlalchemy.orm import Session

from dibbler.models import (
    Product,
    Purchase,
    PurchaseEntry,
    Transaction,
    User,
)

from .helpermenus import Menu


class AddStockMenu(Menu):
    def __init__(self, sql_session: Session):
        super().__init__("Add stock and adjust credit", sql_session)
        self.help_text = """
Enter what you have bought for PVVVV here, along with your user name and how
much money you're due in credits for the purchase when prompted.\n"""
        self.users = []
        self.users = []
        self.products = {}
        self.price = 0

    def _execute(self):
        questions = {
            (
                False,
                False,
            ): 'Enter user id or a string of the form "<number> <product>"',
            (
                False,
                True,
            ): 'Enter user id or more strings of the form "<number> <product>"',
            (True, False): 'Enter a string of the form "<number> <product>"',
            (
                True,
                True,
            ): 'Enter more strings of the form "<number> <product>", or an empty line to confirm',
        }

        self.users = []
        self.products = {}
        self.price = 0

        while True:
            self.print_info()
            self.printc(questions[bool(self.users), bool(len(self.products))])
            thing_price = 0

            # Read in a 'thing' (product or user):
            line = self.input_multiple(
                add_nonexisting=("user", "product"),
                empty_input_permitted=True,
                find_hidden_products=False,
            )

            if line:
                (thing, amount) = line

                if isinstance(thing, Product):
                    self.printc(f"{amount:d} of {thing.name} registered")
                    thing_price = (
                        self.input_int("What did you pay a piece?", 1, 100000, default=thing.price)
                        * amount
                    )
                    self.price += thing_price

                # once we get something in the
                # purchase, we want to protect the
                # user from accidentally killing it
                self.exit_confirm_msg = "Abort transaction?"
            else:
                if not self.complete_input():
                    if self.confirm(
                        "Not enough information entered. Abort transaction?",
                        default=True,
                    ):
                        return False
                    continue
                break

            # Add the thing to the pending adjustments:
            self.add_thing_to_pending(thing, amount, thing_price)

        self.perform_transaction()

    def complete_input(self):
        return bool(self.users) and len(self.products) and self.price

    def print_info(self):
        width = 6 + Product.name_length
        print()
        print(width * "-")
        if self.price:
            print(f"Amount to be credited:{self.price:>{width - 22}}")
        if self.users:
            print("Users to credit:")
            for user in self.users:
                print(f"\t{user.name}")
        print()
        print("Products", end="")
        print("Amount".rjust(width - 8))
        print(width * "-")
        if len(self.products):
            for product in list(self.products.keys()):
                print(f"{product.name}", end="")
                print(f"{self.products[product][0]}".rjust(width - len(product.name)))
                print(width * "-")

    def add_thing_to_pending(
        self,
        thing: User | Product,
        amount: int,
        price: int,
    ):
        if isinstance(thing, User):
            self.users.append(thing)
        elif thing in list(self.products.keys()):
            print("Already added this product, adding amounts")
            self.products[thing][0] += amount
            self.products[thing][1] += price
        else:
            self.products[thing] = [amount, price]

    def perform_transaction(self):
        print("Did you pay a different price?")
        if self.confirm(">", default=False):
            self.price = self.input_int("How much did you pay?", 0, self.price, default=self.price)

        description = self.input_str("Log message", length_range=(0, 50))
        if description == "":
            description = "Purchased products for PVVVV, adjusted credit " + str(self.price)
        for product in self.products:
            value = max(product.stock, 0) * product.price + self.products[product][1]
            old_price = product.price
            old_hidden = product.hidden
            product.price = int(
                ceil(float(value) / (max(product.stock, 0) + self.products[product][0])),
            )
            product.stock = max(
                self.products[product][0], product.stock + self.products[product][0],
            )
            product.hidden = False
            print(
                f"New stock for {product.name}: {product.stock:d}",
                f"- New price: {product.price}" if old_price != product.price else "",
                "- Removed hidden status" if old_hidden != product.hidden else "",
            )

        purchase = Purchase()
        for user in self.users:
            Transaction(user, purchase=purchase, amount=-self.price, description=description)
        for product in self.products:
            PurchaseEntry(purchase, product, -self.products[product][0])

        purchase.perform_soft_purchase(-self.price, round_up=False)
        self.sql_session.add(purchase)

        try:
            self.sql_session.commit()
            print("Success! Transaction performed:")
            # self.print_info()
            for user in self.users:
                print(f"User {user.name}'s credit is now {user.credit:d}")
        except sqlalchemy.exc.SQLAlchemyError as e:
            self.sql_session.rollback()
            print(f"Could not perform transaction: {e}")

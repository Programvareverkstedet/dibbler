import sqlalchemy
from sqlalchemy.orm import Session

from dibbler.conf import config
from dibbler.models import (
    Product,
    Purchase,
    PurchaseEntry,
    Transaction,
    User,
)

from .helpermenus import Menu


class BuyMenu(Menu):
    superfast_mode: bool
    purchase: Purchase

    def __init__(self, sql_session: Session):
        super().__init__("Buy", sql_session)
        self.superfast_mode = False
        self.help_text = """
Each purchase may contain one or more products and one or more buyers.

Enter products (by name or bar code) and buyers (by name or bar code)
in any order.  The information gathered so far is displayed after each
addition, and you can type 'what' at any time to redisplay it.

When finished, write an empty line to confirm the purchase.\n"""

    @staticmethod
    def credit_check(user: User):
        """

        :param user:
        :type user: User
        :rtype: boolean
        """
        assert isinstance(user, User)

        return user.credit > config["limits"]["low_credit_warning_limit"]

    def low_credit_warning(
        self,
        user: User,
        timeout: bool = False,
    ):
        assert isinstance(user, User)

        print(r"***********************************************************************")
        print(r"***********************************************************************")
        print(r"")
        print(r"$$\      $$\  $$$$$$\  $$$$$$$\  $$\   $$\ $$$$$$\ $$\   $$\  $$$$$$\\")
        print(r"$$ | $\  $$ |$$  __$$\ $$  __$$\ $$$\  $$ |\_$$  _|$$$\  $$ |$$  __$$\\")
        print(r"$$ |$$$\ $$ |$$ /  $$ |$$ |  $$ |$$$$\ $$ |  $$ |  $$$$\ $$ |$$ /  \__|")
        print(r"$$ $$ $$\$$ |$$$$$$$$ |$$$$$$$  |$$ $$\$$ |  $$ |  $$ $$\$$ |$$ |$$$$\\")
        print(r"$$$$  _$$$$ |$$  __$$ |$$  __$$< $$ \$$$$ |  $$ |  $$ \$$$$ |$$ |\_$$ |")
        print(r"$$$  / \$$$ |$$ |  $$ |$$ |  $$ |$$ |\$$$ |  $$ |  $$ |\$$$ |$$ |  $$ |")
        print(r"$$  /   \$$ |$$ |  $$ |$$ |  $$ |$$ | \$$ |$$$$$$\ $$ | \$$ |\$$$$$$  |")
        print(r"\__/     \__|\__|  \__|\__|  \__|\__|  \__|\______|\__|  \__| \______/")
        print(r"")
        print(r"***********************************************************************")
        print(r"***********************************************************************")
        print(r"")
        print(
            f"USER {user.name} HAS LOWER CREDIT THAN {config['limits']['low_credit_warning_limit']:d}.",
        )
        print("THIS PURCHASE WILL CHARGE YOUR CREDIT TWICE AS MUCH.")
        print("CONSIDER PUTTING MONEY IN THE BOX TO AVOID THIS.")
        print("")
        print("Do you want to continue with this purchase?")

        if timeout:
            print("THIS PURCHASE WILL AUTOMATICALLY BE PERFORMED IN 3 MINUTES!")
            return self.confirm(prompt=">", default=True, timeout=180)
        return self.confirm(prompt=">", default=True)

    def add_thing_to_purchase(
        self,
        thing: User | Product,
        amount: int = 1,
    ) -> bool:
        if isinstance(thing, User):
            if thing.is_anonymous():
                print("---------------------------------------------")
                print("| You are now purchasing as the user anonym.|")
                print("| You have to put money in the anonym-jar.  |")
                print("---------------------------------------------")

            if not self.credit_check(thing):
                if self.low_credit_warning(
                    user=thing,
                    timeout=self.superfast_mode,
                ):
                    Transaction(thing, purchase=self.purchase, penalty=2)
                else:
                    return False
            else:
                Transaction(thing, purchase=self.purchase)
        elif isinstance(thing, Product):
            if self.purchase.entries:
                for entry in self.purchase.entries:
                    if entry.product == thing:
                        entry.amount += amount
                        return True
            PurchaseEntry(self.purchase, thing, amount)
        return True

    def _execute(
        self,
        initial_contents: list[tuple[User | Product, int]] | None = None,
    ):
        self.print_header()
        self.purchase = Purchase()
        self.exit_confirm_msg = None
        self.superfast_mode = False

        if initial_contents is None:
            initial_contents = []

        for thing, num in initial_contents:
            self.add_thing_to_purchase(thing, num)

        def is_product(candidate):
            return isinstance(candidate[0], Product)

        if len(initial_contents) > 0 and all(map(is_product, initial_contents)):
            self.superfast_mode = True
            print("***********************************************")
            print("****** Buy menu is in SUPERFASTmode[tm]! ******")
            print("*** The purchase will be stored immediately ***")
            print("*** when you enter a user.                  ***")
            print("***********************************************")

        while True:
            self.print_purchase()
            self.printc(
                {
                    (False, False): "Enter user or product identification",
                    (False, True): "Enter user identification or more products",
                    (True, False): "Enter product identification or more users",
                    (
                        True,
                        True,
                    ): "Enter more products or users, or an empty line to confirm",
                }[(len(self.purchase.transactions) > 0, len(self.purchase.entries) > 0)],
            )

            # Read in a 'thing' (product or user):
            line = self.input_multiple(
                add_nonexisting=("user", "product"),
                empty_input_permitted=True,
                find_hidden_products=False,
            )
            if line is not None:
                thing, num = line
            else:
                thing, num = None, 0

            # Possibly exit from the menu:
            if thing is None:
                if not self.complete_input():
                    if self.confirm(
                        "Not enough information entered. Abort purchase?",
                        default=True,
                    ):
                        return False
                    continue
                break
            # once we get something in the
            # purchase, we want to protect the
            # user from accidentally killing it
            self.exit_confirm_msg = "Abort purchase?"

            # Add the thing to our purchase object:
            if not self.add_thing_to_purchase(thing, amount=num):
                continue

            # In super-fast mode, we complete the purchase once we get a user:
            if self.superfast_mode and isinstance(thing, User):
                break

        self.purchase.perform_purchase()
        self.sql_session.add(self.purchase)
        try:
            self.sql_session.commit()
        except sqlalchemy.exc.SQLAlchemyError as e:
            self.sql_session.rollback()
            print(f"Could not store purchase: {e}")
        else:
            print("Purchase stored.")
            self.print_purchase()
            for t in self.purchase.transactions:
                if not t.user.is_anonymous():
                    print(f"User {t.user.name}'s credit is now {t.user.credit:d} kr")
                    if t.user.credit < config["limits"]["low_credit_warning_limit"]:
                        print(
                            f"USER {t.user.name} HAS LOWER CREDIT THAN {config['limits']['low_credit_warning_limit']:d},",
                            "AND SHOULD CONSIDER PUTTING SOME MONEY IN THE BOX.",
                        )

        # Superfast mode skips a linebreak for some reason.
        if self.superfast_mode:
            print("")
        return True

    def complete_input(self):
        return self.purchase.is_complete()

    def format_purchase(self):
        self.purchase.set_price()
        transactions = self.purchase.transactions
        entries = self.purchase.entries
        if len(transactions) == 0 and len(entries) == 0:
            return None
        string = "Purchase:"
        string += "\n  buyers: "
        if len(transactions) == 0:
            string += "(empty)"
        else:
            string += ", ".join(
                [
                    t.user.name + ("*" if not self.credit_check(t.user) else "")
                    for t in transactions
                ],
            )
        string += "\n  products: "
        if len(entries) == 0:
            string += "(empty)"
        else:
            string += "\n    "
            string += "\n    ".join(
                [f"{e.amount:d}x {e.product.name} ({e.product.price:d} kr)" for e in entries],
            )
        if len(transactions) > 1:
            string += f"\n  price per person: {self.purchase.price_per_transaction():d} kr"
            if any(t.penalty > 1 for t in transactions):
                # TODO: Use penalty multiplier instead of 2
                string += f" *({self.purchase.price_per_transaction() * 2:d} kr)"

        string += f"\n  total price: {self.purchase.price:d} kr"

        if any(t.penalty > 1 for t in transactions):
            total = sum(self.purchase.price_per_transaction() * t.penalty for t in transactions)
            string += f"\n  *total with penalty: {total} kr"

        return string

    def print_purchase(self):
        info = self.format_purchase()
        if info is not None:
            self.set_context(info)

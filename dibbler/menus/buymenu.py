import math
from typing import Any

from sqlalchemy.orm import Session

from dibbler.conf import config
from dibbler.models import Product, User
from dibbler.queries import buy_products

from .helpermenus import Menu

PENALTY_MULTIPLIER = 2


class BuyMenu(Menu):
    superfast_mode: bool
    buyers: list[tuple[User, int]]
    products: dict[Product, int]

    def __init__(self, sql_session: Session) -> None:
        super().__init__("Buy", sql_session)
        self.superfast_mode = False
        self.help_text = """
Each purchase may contain one or more products and one or more buyers.

Enter products (by name or barcode) and buyers (by name or barcode)
in any order.  The information gathered so far is displayed after each
addition, and you can type 'what' at any time to redisplay it.

When finished, write an empty line to confirm the purchase.\n"""

    @staticmethod
    def credit_check(user: User) -> bool:
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
    ) -> bool:
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
                    self.buyers.append((thing, PENALTY_MULTIPLIER))
                else:
                    return False
            else:
                self.buyers.append((thing, 1))
        elif isinstance(thing, Product):
            self.products[thing] = self.products.get(thing, 0) + amount
        return True

    def _execute(
        self,
        initial_contents: list[tuple[User | Product, int]] | None = None,
        **_kwargs,
    ) -> bool:
        self.print_header()
        self.buyers = []
        self.products = {}
        self.exit_confirm_msg = None
        self.superfast_mode = False

        if initial_contents is None:
            initial_contents = []

        for thing, num in initial_contents:
            self.add_thing_to_purchase(thing, num)

        def is_product(candidate: Any) -> bool:
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
                }[(len(self.buyers) > 0, len(self.products) > 0)],
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
                        self.sql_session.rollback()
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

        try:
            purchase = buy_products(
                self.sql_session,
                self.buyers,
                list(self.products.items()),
            )
            self.sql_session.commit()
        except Exception as e:
            self.rollback_and_report(
                e,
                "Could not store purchase",
                "Could not store purchase of %r by %r",
                {product.name: amount for product, amount in self.products.items()},
                [user.name for user, _ in self.buyers],
            )
        else:
            print("Purchase stored.")
            self.print_purchase()
            for t in purchase.transactions:
                if not t.user.is_anonymous():
                    print(f"User {t.user.name}'s credit is now {t.user.credit:d} kr")
                    if not self.credit_check(t.user):
                        print(
                            f"USER {t.user.name} HAS LOWER CREDIT THAN {config['limits']['low_credit_warning_limit']:d},",
                            "AND SHOULD CONSIDER PUTTING SOME MONEY IN THE BOX.",
                        )

        # Superfast mode skips a linebreak for some reason.
        if self.superfast_mode:
            print("")
        return True

    def complete_input(self) -> bool:
        return len(self.buyers) > 0 and len(self.products) > 0

    def format_purchase(self) -> str | None:
        if len(self.buyers) == 0 and len(self.products) == 0:
            return None

        price = sum(amount * product.price for product, amount in self.products.items())
        string = "Purchase:"
        string += "\n  buyers: "
        if len(self.buyers) == 0:
            string += "(empty)"
        else:
            string += ", ".join(
                [
                    user.name + ("*" if not self.credit_check(user) else "")
                    for user, _penalty in self.buyers
                ],
            )
        string += "\n  products: "

        if len(self.products) == 0:
            string += "(empty)"
        else:
            string += "\n    "
            string += "\n    ".join(
                [
                    f"{amount:d}x {product.name} ({product.price:d} kr)"
                    for product, amount in self.products.items()
                ],
            )

        string += f"\n  total price: {price:d} kr"

        buyers = self.buyers[:1] if len({user for user, _ in self.buyers}) == 1 else self.buyers

        if len(buyers) > 0:
            price_per_transaction = math.ceil(price / len(buyers))
            if len(buyers) > 1:
                string += f"\n  price per person: {price_per_transaction:d} kr"
                if any(penalty > 1 for _, penalty in buyers):
                    string += f" *({price_per_transaction * PENALTY_MULTIPLIER:d} kr)"

            if any(penalty > 1 for _, penalty in buyers):
                total = sum(price_per_transaction * penalty for _, penalty in buyers)
                string += f"\n  *total with penalty: {total} kr"

        return string

    def print_purchase(self) -> None:
        info = self.format_purchase()
        if info is not None:
            self.set_context(info)

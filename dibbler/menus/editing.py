import sqlalchemy
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from dibbler.models import Product, User
from dibbler.queries import (
    add_bar_code,
    adjust_stock,
    create_product,
    create_user,
    edit_product,
    edit_user,
    merge_products,
    remove_bar_code,
)

from .helpermenus import Menu, Selector

__all__ = [
    "AddUserMenu",
    "AddProductMenu",
    "EditProductMenu",
    "MergeProductsMenu",
    "AdjustStockMenu",
    "CleanupStockMenu",
    "EditUserMenu",
]


class AddUserMenu(Menu):
    def __init__(self, sql_session: Session) -> None:
        super().__init__("Add user", sql_session)

    def _execute(self, **_kwargs) -> None:
        self.print_header()
        username = self.input_str(
            "Username (should be same as PVV username)",
            regex=User.name_re,
            length_range=(1, 10),
        )
        assert username is not None

        cardnum = self.input_str(
            "Card number (optional)",
            regex=User.card_re,
            length_range=(0, 10),
            empty_string_is_none=True,
        )
        if cardnum is not None:
            cardnum = cardnum.lower()

        rfid = self.input_str(
            "RFID (optional)",
            regex=User.rfid_re,
            length_range=(0, 10),
            empty_string_is_none=True,
        )

        try:
            create_user(self.sql_session, username, cardnum, rfid)
            self.sql_session.commit()
            print(f"User {username} stored")
        except (SQLAlchemyError, ValueError) as e:
            self.sql_session.rollback()
            print(f"Could not store user {username}: {e}")
        self.pause()


class EditUserMenu(Menu):
    def __init__(self, sql_session: Session) -> None:
        super().__init__("Edit user", sql_session)
        self.help_text = """
The editable parts of a user are its name, card number and rfid.

First select an existing user, then enter a new name (accept the
default to keep the current one), then a new card number, then rfid
(write an empty line to remove the card number or rfid).
"""

    def _execute(self, **_kwargs) -> None:
        self.print_header()
        user = self.input_user("User")
        self.printc(f"Editing user {user.name}")
        name = self.input_str(
            "Name",
            default=user.name,
            regex=User.name_re,
            length_range=(1, User.name_length),
        )
        assert name is not None

        card_str = f'"{user.card}"' if user.card is not None else "empty"
        card = self.input_str(
            f"Card number (currently {card_str})",
            regex=User.card_re,
            length_range=(0, 10),
            empty_string_is_none=True,
        )
        if card:
            card = card.lower()

        rfid_str = f'"{user.rfid}"' if user.rfid is not None else "empty"
        rfid = self.input_str(
            f"RFID (currently {rfid_str})",
            regex=User.rfid_re,
            length_range=(0, 10),
            empty_string_is_none=True,
        )

        if name == user.name and card == user.card and rfid == user.rfid:
            print("Nothing to edit.")
            self.pause()
            return

        try:
            edit_user(self.sql_session, user, name=name, card=card, rfid=rfid)
            self.sql_session.commit()
            print(f"User {user.name} stored")
        except (SQLAlchemyError, ValueError) as e:
            self.sql_session.rollback()
            print(f"Could not store user {user.name}: {e}")
        self.pause()


class AddProductMenu(Menu):
    def __init__(self, sql_session: Session) -> None:
        super().__init__("Add product", sql_session)

    def _execute(self, **_kwargs) -> None:
        self.print_header()
        bar_code = self.input_str("Barcode", regex=Product.bar_code_re, length_range=(8, 13))
        assert bar_code is not None

        name = self.input_str("Name", regex=Product.name_re, length_range=(1, Product.name_length))
        assert name is not None

        price = self.input_int("Price", 1, 100000)
        try:
            create_product(self.sql_session, bar_code, name, price)
            self.sql_session.commit()
            print(f"Product {name} stored")
        except (SQLAlchemyError, ValueError) as e:
            self.sql_session.rollback()
            print(f"Could not store product {name}: {e}")
        self.pause()


class EditProductMenu(Menu):
    def __init__(self, sql_session: Session) -> None:
        super().__init__("Edit product", sql_session)

    def _execute(self, **_kwargs) -> None:
        self.print_header()
        product = self.input_product("Product")
        self.printc(f"Editing product {product.name}")
        while True:
            selector = Selector(
                f"Do what with {product.name}?",
                sql_session=self.sql_session,
                items=[
                    ("name", "Edit name"),
                    ("price", "Edit price"),
                    ("add_barcode", "Add a barcode"),
                    ("remove_barcode", "Remove a barcode"),
                    ("hidden", "Edit hidden status"),
                    ("store", "Store"),
                ],
            )
            match selector.execute():
                case "name":
                    name = self.input_str(
                        "Name",
                        default=product.name,
                        regex=Product.name_re,
                        length_range=(1, product.name_length),
                    )
                    assert name is not None
                    try:
                        edit_product(self.sql_session, product, name=name)
                    except ValueError as e:
                        print(f"Could not edit name of {product.name}: {e}")

                case "price":
                    price = self.input_int("Price", 1, 100000, default=product.price)
                    try:
                        edit_product(self.sql_session, product, price=price)
                    except ValueError as e:
                        print(f"Could not edit price of {product.name}: {e}")

                case "add_barcode":
                    bar_code = self.input_str(
                        "New barcode",
                        regex=Product.bar_code_re,
                        length_range=(8, 13),
                    )
                    assert bar_code is not None
                    try:
                        add_bar_code(self.sql_session, product, bar_code)
                    except ValueError as e:
                        print(f"Could not add barcode to {product.name}: {e}")

                case "remove_barcode":
                    print("Current barcodes:")
                    for code in sorted(bc.code for bc in product.barcodes):
                        print(f"  - {code}")
                    bar_code = self.input_str(
                        "Barcode to remove",
                        regex=Product.bar_code_re,
                        length_range=(8, 13),
                    )
                    assert bar_code is not None
                    try:
                        remove_bar_code(self.sql_session, product, bar_code)
                    except ValueError as e:
                        print(f"Could not remove barcode from {product.name}: {e}")

                case "hidden":
                    hidden = self.confirm(f"Hidden(currently {product.hidden})", default=False)
                    try:
                        edit_product(self.sql_session, product, hidden=hidden)
                    except ValueError as e:
                        print(f"Could not edit hidden status of {product.name}: {e}")

                case "store":
                    try:
                        self.sql_session.commit()
                        print(f"Product {product.name} stored")
                    except SQLAlchemyError as e:
                        self.sql_session.rollback()
                        print(f"Could not store product {product.name}: {e}")
                    self.pause()
                    return

                case None:
                    print("Edit aborted")
                    return

                case _:
                    print("What what?")


class MergeProductsMenu(Menu):
    def __init__(self, sql_session: Session) -> None:
        super().__init__("Merge products", sql_session)
        self.help_text = """
Merge two duplicate products into one.

Pick product A (the one to delete) and product B (will be kept),
then choose which properties to keep from each product, or edit.
"""

    def _pick(self, label: str, options: list[tuple[str, str]]) -> str:
        selector = Selector(
            f"Which {label} should the merged product have?",
            sql_session=self.sql_session,
            items=options,
        )
        choice = selector.execute()
        assert choice is not None
        return choice

    def _execute(self, **_kwargs) -> None:
        self.print_header()
        user = self.input_user("User")
        source = self.input_product("Product to delete (A)")
        target = self.input_product("Product to keep (B)")

        if source.id == target.id:
            print("Cannot merge a product into itself.")
            self.pause()
            return

        self.printc(f"Merging {source.name} (A) into {target.name} (B)")

        if source.name == target.name:
            name = source.name
        else:
            match self._pick(
                "name",
                [
                    ("a", f'A\'s name: "{source.name}"'),
                    ("b", f'B\'s name: "{target.name}"'),
                    ("custom", "Enter a custom name"),
                ],
            ):
                case "a":
                    name = source.name
                case "b":
                    name = target.name
                case _:
                    name = self.input_str(
                        "Name",
                        regex=Product.name_re,
                        length_range=(1, Product.name_length),
                    )
                    assert name is not None

        if source.price == target.price:
            price = source.price
        else:
            match self._pick(
                "price",
                [
                    ("a", f"A's price: {source.price}"),
                    ("b", f"B's price: {target.price}"),
                    ("custom", "Enter a custom price"),
                ],
            ):
                case "a":
                    price = source.price
                case "b":
                    price = target.price
                case _:
                    price = self.input_int("Price", 1, 100000)

        if source.hidden == target.hidden:
            hidden = source.hidden
        else:
            match self._pick(
                "hidden status",
                [
                    ("a", f"A's hidden status: {source.hidden}"),
                    ("b", f"B's hidden status: {target.hidden}"),
                    ("custom", "Enter a custom hidden status"),
                ],
            ):
                case "a":
                    hidden = source.hidden
                case "b":
                    hidden = target.hidden
                case _:
                    hidden = self.confirm("Hidden", default=target.hidden)

        # NOTE: Unlike the other properties, we deliberately always ask about stock.
        #       It's not sane to assume anything here.
        match self._pick(
            "stock",
            [
                ("a", f"A's stock: {source.stock}"),
                ("b", f"B's stock: {target.stock}"),
                ("sum", f"Sum of both: {source.stock + target.stock}"),
                ("custom", "Enter a custom stock"),
            ],
        ):
            case "a":
                stock = source.stock
            case "b":
                stock = target.stock
            case "sum":
                stock = source.stock + target.stock
            case _:
                stock = self.input_int("Stock", 0, 100000)

        try:
            merge_products(
                self.sql_session,
                user,
                source,
                target,
                name=name,
                price=price,
                hidden=hidden,
                stock=stock,
            )
            self.sql_session.commit()
            print(f"Product {source.name} merged into {target.name}")
        except (ValueError, SQLAlchemyError) as e:
            self.sql_session.rollback()
            print(f"Could not merge products: {e}")
        self.pause()


class AdjustStockMenu(Menu):
    def __init__(self, sql_session: Session) -> None:
        super().__init__("Adjust stock", sql_session)

    def _execute(self, **_kwargs) -> None:
        self.print_header()
        user = self.input_user("User")
        product = self.input_product("Product")

        print(f"The stock of this product is: {product.stock:d}")
        print("Write the number of products you have added to the stock")
        print("Alternatively, correct the stock for any mistakes")
        add_stock = self.input_int("Added stock", -1000, 1000, zero_allowed=False)
        if add_stock > 0:
            print(f"You added {add_stock:d} to the stock of {product}")
        else:
            print(f"You removed {(add_stock * -1):d} from the stock of {product}")

        try:
            adjust_stock(self.sql_session, user, product, add_stock)
            self.sql_session.commit()
            print("Stock is now stored")
            self.pause()
        except (SQLAlchemyError, ValueError) as e:
            self.sql_session.rollback()
            print(f"Could not store stock: {e}")
            self.pause()
            return
        print(f"The stock is now {product.stock:d}")


class CleanupStockMenu(Menu):
    def __init__(self, sql_session: Session) -> None:
        super().__init__("Stock Cleanup", sql_session)

    def _execute(self, **_kwargs) -> None:
        self.print_header()
        user = self.input_user("User")

        products = self.sql_session.query(Product).filter(Product.stock != 0).all()

        print("Every product in stock will be printed.")
        print("Entering no value will keep current stock or set it to 0 if it is negative.")
        print("Entering a value will set current stock to that value.")
        print("Press enter to begin.")

        self.pause()

        changed_products = []

        for product in products:
            oldstock = product.stock
            newstock = self.input_int(product.name, 0, 10000, default=max(0, oldstock))
            if newstock != oldstock:
                try:
                    adjust_stock(self.sql_session, user, product, newstock - oldstock)
                except ValueError as e:
                    print(f"Could not adjust stock of {product.name}: {e}")
                    continue
                changed_products.append((product, oldstock))

        try:
            self.sql_session.commit()
            print("New stocks are now stored.")
            self.pause()
        except SQLAlchemyError as e:
            self.sql_session.rollback()
            print(f"Could not store stock: {e}")
            self.pause()
            return

        for p in changed_products:
            print(p[0].name, ".", p[1], "->", p[0].stock)

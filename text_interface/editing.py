import sqlalchemy
from db import User, Product
from text_interface.helpermenus import Menu, Selector

__all__ = ["AddUserMenu", "AddProductMenu", "EditProductMenu", "AdjustStockMenu", "CleanupStockMenu", "EditUserMenu"]


class AddUserMenu(Menu):
    def __init__(self):
        Menu.__init__(self, 'Add user', uses_db=True)

    def _execute(self):
        self.print_header()
        username = self.input_str('Username (should be same as PVV username)', regex=User.name_re, length_range=(1, 10))
        cardnum = self.input_str('Card number (optional)', regex=User.card_re, length_range=(0, 10))
        cardnum = cardnum.lower()
        rfid = self.input_str('RFID (optional)', regex=User.rfid_re, length_range=(0, 10))
        user = User(username, cardnum, rfid)
        self.session.add(user)
        try:
            self.session.commit()
            print(f'User {username} stored')
        except sqlalchemy.exc.IntegrityError as e:
            print(f'Could not store user {username}: {e}')
        self.pause()


class EditUserMenu(Menu):
    def __init__(self):
        Menu.__init__(self, 'Edit user', uses_db=True)
        self.help_text = '''
The only editable part of a user is its card number and rfid.

First select an existing user, then enter a new card number for that
user, then rfid (write an empty line to remove the card number or rfid).
'''

    def _execute(self):
        self.print_header()
        user = self.input_user('User')
        self.printc(f'Editing user {user.name}')
        card_str = f'"{user.card}"' if user.card is not None else 'empty'
        user.card = self.input_str(f'Card number (currently {card_str})',
                                   regex=User.card_re, length_range=(0, 10),
                                   empty_string_is_none=True)
        if user.card:
            user.card = user.card.lower()

        rfid_str = f'"{user.rfid}"' if user.rfid is not None else 'empty'
        user.rfid = self.input_str(f'RFID (currently {rfid_str})',
                                   regex=User.rfid_re, length_range=(0, 10),
                                   empty_string_is_none=True)
        try:
            self.session.commit()
            print(f'User {user.name} stored')
        except sqlalchemy.exc.SQLAlchemyError as e:
            print(f'Could not store user {user.name}: {e}')
        self.pause()


class AddProductMenu(Menu):
    def __init__(self):
        Menu.__init__(self, 'Add product', uses_db=True)

    def _execute(self):
        self.print_header()
        bar_code = self.input_str('Bar code', regex=Product.bar_code_re, length_range=(8, 13))
        name = self.input_str('Name', regex=Product.name_re, length_range=(1, Product.name_length))
        price = self.input_int('Price', allowed_range=(1, 100000))
        product = Product(bar_code, name, price)
        self.session.add(product)
        try:
            self.session.commit()
            print(f'Product {name} stored')
        except sqlalchemy.exc.SQLAlchemyError as e:
            print(f'Could not store product {name}: {e}')
        self.pause()


class EditProductMenu(Menu):
    def __init__(self):
        Menu.__init__(self, 'Edit product', uses_db=True)

    def _execute(self):
        self.print_header()
        product = self.input_product('Product')
        self.printc(f'Editing product {product.name}')
        while True:
            selector = Selector(f'Do what with {product.name}?',
                                items=[('name', 'Edit name'),
                                       ('price', 'Edit price'),
                                       ('barcode', 'Edit barcode'),
                                       ('hidden', 'Edit hidden status'),
                                       ('store', 'Store')])
            what = selector.execute()
            if what == 'name':
                product.name = self.input_str('Name', default=product.name, regex=Product.name_re,
                                              length_range=(1, product.name_length))
            elif what == 'price':
                product.price = self.input_int('Price', default=product.price, allowed_range=(1, 100000))
            elif what == 'barcode':
                product.bar_code = self.input_str('Bar code', default=product.bar_code, regex=Product.bar_code_re,
                                                  length_range=(8, 13))
            elif what == 'hidden':
                product.hidden = self.confirm(f'Hidden(currently {product.hidden})', default=False)
            elif what == 'store':
                try:
                    self.session.commit()
                    print(f'Product {product.name} stored')
                except sqlalchemy.exc.SQLAlchemyError as e:
                    print(f'Could not store product {product.name}: {e}')
                self.pause()
                return
            elif what is None:
                print('Edit aborted')
                return
            else:
                print('What what?')


class AdjustStockMenu(Menu):
    def __init__(self):
        Menu.__init__(self, 'Adjust stock', uses_db=True)

    def _execute(self):
        self.print_header()
        product = self.input_product('Product')

        print(f'The stock of this product is: {product.stock:d}')
        print('Write the number of products you have added to the stock')
        print('Alternatively, correct the stock for any mistakes')
        add_stock = self.input_int('Added stock', allowed_range=(-1000, 1000))
        # TODO: Print something else when adding negative stock?
        print(f'You added {add_stock:d} to the stock of {product}')

        product.stock += add_stock

        try:
            self.session.commit()
            print('Stock is now stored')
            self.pause()
        except sqlalchemy.exc.SQLAlchemyError as e:
            print(f'Could not store stock: {e}')
            self.pause()
            return
        print(f'The stock is now {product.stock:d}')


class CleanupStockMenu(Menu):
    def __init__(self):
        Menu.__init__(self, 'Stock Cleanup', uses_db=True)

    def _execute(self):
        self.print_header()

        products = self.session.query(Product).filter(Product.stock != 0).all()

        print("Every product in stock will be printed.")
        print("Entering no value will keep current stock or set it to 0 if it is negative.")
        print("Entering a value will set current stock to that value.")
        print("Press enter to begin.")

        self.pause()

        changed_products = []

        for product in products:
            oldstock = product.stock
            product.stock = self.input_int(product.name, allowed_range=(0, 10000), default=max(0, oldstock))
            self.session.add(product)
            if oldstock != product.stock:
                changed_products.append((product, oldstock))

        try:
            self.session.commit()
            print('New stocks are now stored.')
            self.pause()
        except sqlalchemy.exc.SQLAlchemyError as e:
            print(f'Could not store stock: {e}')
            self.pause()
            return

        for p in changed_products:
            print(p[0].name, ".", p[1], "->", p[0].stock)

import sqlalchemy
from db import User, Product
from text_interface.helpermenus import Menu, Selector

__all__ = ["AddUserMenu", "AddProductMenu", "EditProductMenu", "AdjustStockMenu", "CleanupStockMenu", "EditUserMenu"]


class AddUserMenu(Menu):
    def __init__(self):
        Menu.__init__(self, 'Add user', uses_db=True)

    def _execute(self):
        self.print_header()
        username = self.input_str('Username (should be same as PVV username)> ', User.name_re, (1, 10))
        cardnum = self.input_str('Card number (optional)> ', User.card_re, (0, 10))
        cardnum = cardnum.lower()
        rfid = self.input_str('RFID (optional)> ', User.rfid_re, (0, 10))
        user = User(username, cardnum, rfid)
        self.session.add(user)
        try:
            self.session.commit()
            print 'User %s stored' % username
        except sqlalchemy.exc.IntegrityError, e:
            print 'Could not store user %s: %s' % (username, e)
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
        user = self.input_user('User> ')
        self.printc('Editing user %s' % user.name)
        card_str = '"%s"' % user.card
        if user.card is None:
            card_str = 'empty'
        user.card = self.input_str('Card number (currently %s)> ' % card_str,
                                   User.card_re, (0, 10),
                                   empty_string_is_none=True)
        if user.card:
            user.card = user.card.lower()

        rfid_str = '"%s"' % user.rfid
        if user.rfid is None:
            rfid_str = 'empty'
        user.rfid = self.input_str('RFID (currently %s)> ' % rfid_str,
                                   User.rfid_re, (0, 10),
                                   empty_string_is_none=True)
        try:
            self.session.commit()
            print 'User %s stored' % user.name
        except sqlalchemy.exc.SQLAlchemyError, e:
            print 'Could not store user %s: %s' % (user.name, e)
        self.pause()


class AddProductMenu(Menu):
    def __init__(self):
        Menu.__init__(self, 'Add product', uses_db=True)

    def _execute(self):
        self.print_header()
        bar_code = self.input_str('Bar code> ', Product.bar_code_re, (8, 13))
        name = self.input_str('Name> ', Product.name_re, (1, Product.name_length))
        price = self.input_int('Price> ', (1, 100000))
        product = Product(bar_code, name, price)
        self.session.add(product)
        try:
            self.session.commit()
            print 'Product %s stored' % name
        except sqlalchemy.exc.SQLAlchemyError, e:
            print 'Could not store product %s: %s' % (name, e)
        self.pause()


class EditProductMenu(Menu):
    def __init__(self):
        Menu.__init__(self, 'Edit product', uses_db=True)

    def _execute(self):
        self.print_header()
        product = self.input_product('Product> ')
        self.printc('Editing product %s' % product.name)
        while True:
            selector = Selector('Do what with %s?' % product.name,
                                items=[('name', 'Edit name'),
                                       ('price', 'Edit price'),
                                       ('barcode', 'Edit barcode'),
                                       ('hidden', 'Edit hidden status'),
                                       ('store', 'Store')])
            what = selector.execute()
            if what == 'name':
                product.name = self.input_str('Name[%s]> ' % product.name, Product.name_re, (1, product.name_length))
            elif what == 'price':
                product.price = self.input_int('Price[%s]> ' % product.price, (1, 100000))
            elif what == 'barcode':
                product.bar_code = self.input_str('Bar code[%s]> ' % product.bar_code, Product.bar_code_re, (8, 13))
            elif what == 'hidden':
                product.hidden = self.confirm('Hidden[%s]' % ("Y" if product.hidden else "N"), False)
            elif what == 'store':
                try:
                    self.session.commit()
                    print 'Product %s stored' % product.name
                except sqlalchemy.exc.SQLAlchemyError, e:
                    print 'Could not store product %s: %s' % (product.name, e)
                self.pause()
                return
            elif what is None:
                print 'Edit aborted'
                return
            else:
                print 'What what?'


class AdjustStockMenu(Menu):
    def __init__(self):
        Menu.__init__(self, 'Adjust stock', uses_db=True)

    def _execute(self):
        self.print_header()
        product = self.input_product('Product> ')

        print 'The stock of this product is: %d ' % product.stock
        print 'Write the number of products you have added to the stock'
        print 'Alternatively, correct the stock for any mistakes'
        add_stock = self.input_int('Added stock> ', (-1000, 1000))
        print 'You added %d to the stock of %s' % (add_stock, product)

        product.stock += add_stock

        print 'The stock is now %d' % product.stock

        try:
            self.session.commit()
            print 'Stock is now stored'
            self.pause()
        except sqlalchemy.exc.SQLAlchemyError, e:
            print 'Could not store stock: %s' % e
            self.pause()
            return
        print 'The stock is now %d' % product.stock


class CleanupStockMenu(Menu):
    def __init__(self):
        Menu.__init__(self, 'Stock Cleanup', uses_db=True)

    def _execute(self):
        self.print_header()

        products = self.session.query(Product).filter(Product.stock != 0).all()

        print "Every product in stock will be printed."
        print "Entering no value will keep current stock or set it to 0 if it is negative."
        print "Entering a value will set current stock to that value."
        print "Press enter to begin."

        self.pause()

        changed_products = []

        for product in products:
            oldstock = product.stock
            product.stock = self.input_int(product.name, (0, 10000), default=max(0, oldstock))
            self.session.add(product)
            if oldstock != product.stock:
                changed_products.append((product, oldstock))

        try:
            self.session.commit()
            print 'New stocks are now stored.'
            self.pause()
        except sqlalchemy.exc.SQLAlchemyError, e:
            print 'Could not store stock: %s' % e
            self.pause()
            return

        for p in changed_products:
            print p[0].name, ".", p[1], "->", p[0].stock

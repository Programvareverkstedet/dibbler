import conf
import sqlalchemy
from db import Transaction, Product, User
from helpers import less
from text_interface.helpermenus import Menu, Selector


class TransferMenu(Menu):
    def __init__(self):
        Menu.__init__(self, 'Transfer credit between users',
                      uses_db=True)

    def _execute(self):
        self.print_header()
        amount = self.input_int('Transfer amount> ', (1, 100000))
        self.set_context('Transfering %d kr' % amount, display=False)
        user1 = self.input_user('From user> ')
        self.add_to_context(' from ' + user1.name)
        user2 = self.input_user('To user> ')
        self.add_to_context(' to ' + user2.name)
        comment = self.input_str('Comment> ')
        self.add_to_context(' (comment) ' + user2.name)

        t1 = Transaction(user1, amount,
                         'transfer to ' + user2.name + ' "' + comment + '"')
        t2 = Transaction(user2, -amount,
                         'transfer from ' + user1.name + ' "' + comment + '"')
        t1.perform_transaction()
        t2.perform_transaction()
        self.session.add(t1)
        self.session.add(t2)
        try:
            self.session.commit()
            print('Transfered %d kr from %s to %s' % (amount, user1, user2))
            print('User %s\'s credit is now %d kr' % (user1, user1.credit))
            print('User %s\'s credit is now %d kr' % (user2, user2.credit))
            print('Comment: %s' % comment)
        except sqlalchemy.exc.SQLAlchemyError as e:
            print('Could not perform transfer: %s' % e)
            # self.pause()


class ShowUserMenu(Menu):
    def __init__(self):
        Menu.__init__(self, 'Show user', uses_db=True)

    def _execute(self):
        self.print_header()
        user = self.input_user('User name, card number or RFID> ')
        print('User name: %s' % user.name)
        print('Card number: %s' % user.card)
        print('RFID: %s' % user.rfid)
        print('Credit: %s kr' % user.credit)
        selector = Selector('What do you want to know about %s?' % user.name,
                            items=[('transactions', 'Recent transactions (List of last ' + str(
                                conf.user_recent_transaction_limit) + ')'),
                                   ('products', 'Which products %s has bought, and how many' % user.name),
                                   ('transactions-all', 'Everything (List of all transactions)')])
        what = selector.execute()
        if what == 'transactions':
            self.print_transactions(user, conf.user_recent_transaction_limit)
        elif what == 'products':
            self.print_purchased_products(user)
        elif what == 'transactions-all':
            self.print_all_transactions(user)
        else:
            print('What what?')

    @staticmethod
    def print_all_transactions(user):
        num_trans = len(user.transactions)
        string = '%s\'s transactions (%d):\n' % (user.name, num_trans)
        for t in user.transactions[::-1]:
            string += ' * %s: %s %d kr, ' % \
                      (t.time.strftime('%Y-%m-%d %H:%M'),
                       {True: 'in', False: 'out'}[t.amount < 0],
                       abs(t.amount))
            if t.purchase:
                string += 'purchase ('
                string += ', '.join([e.product.name for e in t.purchase.entries])
                string += ')'
                if t.penalty > 1:
                    string += ' * %dx penalty applied' % t.penalty
            else:
                string += t.description
            string += '\n'
        less(string)

    @staticmethod
    def print_transactions(user, limit=10):
        num_trans = len(user.transactions)
        if num_trans <= limit:
            string = '%s\'s transactions (%d):\n' % (user.name, num_trans)
        else:
            string = '%s\'s transactions (%d, showing only last %d):\n' % (user.name, num_trans, limit)
        for t in user.transactions[-1:-limit - 1:-1]:
            string += ' * %s: %s %d kr, ' % \
                      (t.time.strftime('%Y-%m-%d %H:%M'),
                       {True: 'in', False: 'out'}[t.amount < 0],
                       abs(t.amount))
            if t.purchase:
                string += 'purchase ('
                string += ', '.join([e.product.name for e in t.purchase.entries])
                string += ')'
                if t.penalty > 1:
                    string += ' * %dx penalty applied' % t.penalty
            else:
                string += t.description
            string += '\n'
        less(string)

    @staticmethod
    def print_purchased_products(user):
        products = []
        for ref in user.products:
            product = ref.product
            count = ref.count
            if count > 0:
                products.append((product, count))
        num_products = len(products)
        if num_products == 0:
            print('No products purchased yet')
        else:
            text = ''
            text += 'Products purchased:\n'
            for product, count in products:
                text += '{0:<47} {1:>3}\n'.format(product.name, count)
            less(text)


class UserListMenu(Menu):
    def __init__(self):
        Menu.__init__(self, 'User list', uses_db=True)

    def _execute(self):
        self.print_header()
        user_list = self.session.query(User).all()
        total_credit = self.session.query(sqlalchemy.func.sum(User.credit)).first()[0]

        line_format = '%-12s | %6s\n'
        hline = '---------------------\n'
        text = ''
        text += line_format % ('username', 'credit')
        text += hline
        for user in user_list:
            text += line_format % (user.name, user.credit)
        text += hline
        text += line_format % ('total credit', total_credit)
        less(text)


class AdjustCreditMenu(Menu):  # reimplements ChargeMenu; these should be combined to one
    def __init__(self):
        Menu.__init__(self, 'Adjust credit', uses_db=True)

    def _execute(self):
        self.print_header()
        user = self.input_user('User> ')
        print('User %s\'s credit is %d kr' % (user.name, user.credit))
        self.set_context('Adjusting credit for user %s' % user.name, display=False)
        print('(Note on sign convention: Enter a positive amount here if you have')
        print('added money to the PVVVV money box, a negative amount if you have')
        print('taken money from it)')
        amount = self.input_int('Add amount> ', (-100000, 100000))
        print('(The "log message" will show up in the transaction history in the')
        print('"Show user" menu.  It is not necessary to enter a message, but it')
        print('might be useful to help you remember why you adjusted the credit)')
        description = self.input_str('Log message> ', length_range=(0, 50))
        if description == '':
            description = 'manually adjusted credit'
        transaction = Transaction(user, -amount, description)
        transaction.perform_transaction()
        self.session.add(transaction)
        try:
            self.session.commit()
            print('User %s\'s credit is now %d kr' % (user.name, user.credit))
        except sqlalchemy.exc.SQLAlchemyError as e:
            print('Could not store transaction: %s' % e)
            # self.pause()


class ProductListMenu(Menu):
    def __init__(self):
        Menu.__init__(self, 'Product list', uses_db=True)

    def _execute(self):
        self.print_header()
        text = ''
        product_list = self.session.query(Product).filter(Product.hidden.is_(False)).order_by(Product.stock.desc())
        total_value = 0
        for p in product_list:
            total_value += p.price * p.stock
        line_format = '%-15s | %5s | %-' + str(Product.name_length) + 's | %5s \n'
        text += line_format % ('bar code', 'price', 'name', 'stock')
        text += 78 * '-' + '\n'
        for p in product_list:
            text += line_format % (p.bar_code, p.price, p.name, p.stock)
        text += 78 * '-' + '\n'
        text += line_format % ('Total value', total_value, '', '',)
        less(text)


class ProductSearchMenu(Menu):
    def __init__(self):
        Menu.__init__(self, 'Product search', uses_db=True)

    def _execute(self):
        self.print_header()
        self.set_context('Enter (part of) product name or bar code')
        product = self.input_product()
        print('Result: %s, price: %d kr, bar code: %s, stock: %d, hidden: %s' % (product.name, product.price,
                                                                                 product.bar_code, product.stock,
                                                                                 ("Y" if product.hidden else "N")))
        # self.pause()

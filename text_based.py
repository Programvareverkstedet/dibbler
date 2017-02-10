#!/usr/bin/python
# -*- coding: utf-8 -*-

import random
import re
import sys
import traceback
from select import select

import sqlalchemy
from helpers import *
from sqlalchemy import desc
from sqlalchemy.sql import func
from statistikkHelpers import statisticsTextOnly

random.seed()
exit_commands = ['exit', 'abort', 'quit', 'bye', 'eat flaming death', 'q']
help_commands = ['help', '?']
context_commands = ['what', '??']
local_help_commands = ['help!', '???']
faq_commands = ['faq']
restart_commands = ['restart']


class ExitMenu(Exception):
    pass


class Menu(object):
    def __init__(self, name, items=None, prompt='> ',
                 return_index=True,
                 exit_msg=None, exit_confirm_msg=None, exit_disallowed_msg=None,
                 help_text=None, uses_db=False):
        self.name = name
        self.items = items if items is not None else []
        self.prompt = prompt
        self.return_index = return_index
        self.exit_msg = exit_msg
        self.exit_confirm_msg = exit_confirm_msg
        self.exit_disallowed_msg = exit_disallowed_msg
        self.help_text = help_text
        self.context = None
        self.header_format = '[%s]'
        self.uses_db = uses_db
        self.session = None

    def exit_menu(self):
        if self.exit_disallowed_msg is not None:
            print self.exit_disallowed_msg
            return
        if self.exit_confirm_msg is not None:
            if not self.confirm(self.exit_confirm_msg, default=True):
                return
        raise ExitMenu()

    def at_exit(self):
        if self.exit_msg:
            print self.exit_msg

    def set_context(self, string, display=True):
        self.context = string
        if self.context is not None and display:
            print self.context

    def add_to_context(self, string):
        self.context += string

    def printc(self, string):
        print string
        if self.context is None:
            self.context = string
        else:
            self.context += '\n' + string

    def show_context(self):
        print self.header_format % self.name
        if self.context is not None:
            print self.context

    def item_is_submenu(self, i):
        return isinstance(self.items[i], Menu)

    def item_name(self, i):
        if self.item_is_submenu(i):
            return self.items[i].name
        elif isinstance(self.items[i], tuple):
            return self.items[i][1]
        else:
            return self.items[i]

    def item_value(self, i):
        if isinstance(self.items[i], tuple):
            return self.items[i][0]
        if self.return_index:
            return i
        return self.items[i]

    def input_str(self, prompt=None, regex=None, length_range=(None, None),
                  empty_string_is_none=False, timeout=None):
        if prompt is None:
            prompt = self.prompt
        if regex is not None:
            while True:
                result = self.input_str(prompt, length_range=length_range,
                                        empty_string_is_none=empty_string_is_none)
                if result is None or re.match(regex + '$', result):
                    return result
                else:
                    print 'Value must match regular expression "%s"' % regex
        if length_range != (None, None):
            while True:
                result = self.input_str(prompt, empty_string_is_none=empty_string_is_none)
                if result is None:
                    length = 0
                else:
                    length = len(result)
                if ((length_range[0] and length < length_range[0]) or
                        (length_range[1] and length > length_range[1])):
                    if length_range[0] and length_range[1]:
                        print 'Value must have length in range [%d,%d]' % length_range
                    elif length_range[0]:
                        print 'Value must have length at least %d' % length_range[0]
                    else:
                        print 'Value must have length at most %d' % length_range[1]
                else:
                    return result
        while True:
            try:
                # result = None
                # It is replaced either way
                if timeout:
                    # assuming line buffering
                    sys.stdout.write(safe_str(prompt))
                    sys.stdout.flush()
                    rlist, _, _ = select([sys.stdin], [], [], timeout)
                    if not rlist:
                        # timeout occurred, simulate empty line
                        result = ''
                    else:
                        result = unicode(raw_input(), conf.input_encoding).strip()
                else:
                    result = unicode(raw_input(safe_str(prompt)), conf.input_encoding).strip()
            except EOFError:
                print 'quit'
                self.exit_menu()
                continue
            if result in exit_commands:
                self.exit_menu()
                continue
            if result in help_commands:
                self.general_help()
                continue
            if result in local_help_commands:
                self.local_help()
                continue
            if result in context_commands:
                self.show_context()
                print 'hei hello'
                continue
            if result in faq_commands:
                FAQMenu().execute()
                continue
            if result in restart_commands:
                if self.confirm('Restart Dibbler?'):
                    restart()
                continue
            if empty_string_is_none and result == '':
                return None
            return result

    def special_input_choice(self, in_str):
        """
        Handle choices which are not simply menu items.

        Override this in subclasses to implement magic menu
        choices.  Return True if str was some valid magic menu
        choice, False otherwise.
        """
        return False

    def input_choice(self, number_of_choices, prompt=None):
        if prompt is None:
            prompt = self.prompt
        while True:
            result = self.input_str(prompt)
            if result == '':
                print 'Please enter something'
            # 'c' i hovedmenyen for å endre farger
            elif result == 'c':
                os.system('echo -e "\033[' + str(random.randint(40, 49)) + ';' + str(random.randint(30, 37)) + ';5m"')
                os.system('clear')
                self.show_context()

            # 'cs' i hovedmenyen for å sette standardfarger
            elif result == 'cs':
                os.system('echo -e "\033[0m"')
                os.system('clear')
                self.show_context()

            else:
                if result.isdigit():
                    choice = int(result)
                    if choice == 0 and 10 <= number_of_choices:
                        return 10
                    if choice > 0 and choice <= number_of_choices:
                        return choice
                if not self.special_input_choice(result):
                    self.invalid_menu_choice(result)

    def invalid_menu_choice(self, in_str):
        print 'Please enter a valid choice.'

    def input_int(self, prompt=None, allowed_range=(None, None), null_allowed=False, default=None):
        if prompt is None:
            prompt = self.prompt
        if default is not None:
            prompt += ("[%s] " % default)
        while True:
            result = self.input_str(prompt)
            if result == '':
                if default is not None:
                    return default
                elif null_allowed:
                    return False
            try:
                value = int(result)
                if ((allowed_range[0] and value < allowed_range[0]) or
                        (allowed_range[1] and value > allowed_range[1])):
                    if allowed_range[0] and allowed_range[1]:
                        print 'Value must be in range [%d,%d]' % allowed_range
                    elif allowed_range[0]:
                        print 'Value must be at least %d' % allowed_range[0]
                    else:
                        print 'Value must be at most %d' % allowed_range[1]
                else:
                    return value
            except ValueError:
                print "Please enter an integer"

    def input_user(self, prompt=None):
        user = None
        while user is None:
            user = self.retrieve_user(self.input_str(prompt))
        return user

    def retrieve_user(self, search_str):
        return self.search_ui(search_user, search_str, 'user')

    def input_product(self, prompt=None):
        product = None
        while product is None:
            product = self.retrieve_product(self.input_str(prompt))
        return product

    def retrieve_product(self, search_str):
        return self.search_ui(search_product, search_str, 'product')

    def input_thing(self, prompt=None, permitted_things=('user', 'product'),
                    add_nonexisting=(), empty_input_permitted=False, find_hidden_products=True):
        result = None
        while result is None:
            search_str = self.input_str(prompt)
            if search_str == '' and empty_input_permitted:
                return None
            result = self.search_for_thing(search_str, permitted_things, add_nonexisting, find_hidden_products)
        return result

    def input_multiple(self, prompt=None, permitted_things=('user', 'product'),
                       add_nonexisting=(), empty_input_permitted=False, find_hidden_products=True):
        result = None
        num = 0
        while result is None:
            search_str = self.input_str(prompt)
            search_lst = search_str.split(" ")
            if search_str == '' and empty_input_permitted:
                return None
            else:
                result = self.search_for_thing(search_str, permitted_things, add_nonexisting, find_hidden_products)
                num = 1

                if (result is None) and (len(search_lst) > 1):
                    print 'Interpreting input as "<number> <product>"'
                    try:
                        num = int(search_lst[0])
                        result = self.search_for_thing(" ".join(search_lst[1:]), permitted_things, add_nonexisting,
                                                       find_hidden_products)
                    # Her kan det legges inn en except ValueError,
                    # men da blir det fort mye plaging av brukeren
                    except Exception as e:
                        print(e)
        return result, num

    def search_for_thing(self, search_str, permitted_things=('user', 'product'),
                         add_nonexisting=(), find_hidden_products=True):
        search_fun = {'user': search_user,
                      'product': search_product}
        results = {}
        result_values = {}
        for thing in permitted_things:
            results[thing] = search_fun[thing](search_str, self.session, find_hidden_products)
            result_values[thing] = self.search_result_value(results[thing])
        selected_thing = argmax(result_values)
        if not results[selected_thing]:
            thing_for_type = {'card': 'user', 'username': 'user',
                              'bar_code': 'product', 'rfid': 'rfid'}
            type_guess = guess_data_type(search_str)
            if type_guess is not None and thing_for_type[type_guess] in add_nonexisting:
                return self.search_add(search_str)
            # print 'No match found for "%s".' % search_str
            return None
        return self.search_ui2(search_str, results[selected_thing], selected_thing)

    def search_result_value(self, result):
        if result is None:
            return 0
        if not isinstance(result, list):
            return 3
        if len(result) == 0:
            return 0
        if len(result) == 1:
            return 2
        return 1

    def search_add(self, string):
        type_guess = guess_data_type(string)
        if type_guess == 'username':
            print '"%s" looks like a username, but no such user exists.' % string
            if self.confirm('Create user %s?' % string):
                user = User(string, None)
                self.session.add(user)
                return user
            return None
        if type_guess == 'card':
            selector = Selector('"%s" looks like a card number, but no user with that card number exists.' % string,
                                [('create', 'Create user with card number %s' % string),
                                 ('set', 'Set card number of an existing user to %s' % string)])
            selection = selector.execute()
            if selection == 'create':
                username = self.input_str('Username for new user (should be same as PVV username)> ',
                                          User.name_re, (1, 10))
                user = User(username, string)
                self.session.add(user)
                return user
            if selection == 'set':
                user = self.input_user('User to set card number for> ')
                old_card = user.card
                user.card = string
                print 'Card number of %s set to %s (was %s)' % (user.name, string, old_card)
                return user
            return None
        if type_guess == 'bar_code':
            print '"%s" looks like the bar code for a product, but no such product exists.' % string
            return None

    def search_ui(self, search_fun, search_str, thing):
        result = search_fun(search_str, self.session)
        return self.search_ui2(search_str, result, thing)

    def search_ui2(self, search_str, result, thing):
        if not isinstance(result, list):
            return result
        if len(result) == 0:
            print 'No %ss matching "%s"' % (thing, search_str)
            return None
        if len(result) == 1:
            msg = 'One %s matching "%s": %s.  Use this?' % \
                  (thing, search_str, unicode(result[0]))
            if self.confirm(msg, default=True):
                return result[0]
            return None
        limit = 9
        if len(result) > limit:
            select_header = '%d %ss matching "%s"; showing first %d' % \
                            (len(result), thing, search_str, limit)
            select_items = result[:limit]
        else:
            select_header = '%d %ss matching "%s"' % \
                            (len(result), thing, search_str)
            select_items = result
        selector = Selector(select_header, items=select_items,
                            return_index=False)
        return selector.execute()

    def confirm(self, prompt, default=None, timeout=None):
        return ConfirmMenu(prompt, default, timeout).execute()

    def print_header(self):
        print ""
        print self.header_format % self.name

    def pause(self):
        self.input_str('.')

    def general_help(self):
        print '''
       DIBBLER HELP

       The following commands are recognized (almost) everywhere:

        help, ?          -- display this help
        what, ??         -- redisplay the current context
        help!, ???       -- display context-specific help (if any)
        faq              -- display frequently asked questions (with answers)
        exit, quit, etc. -- exit from the current menu

       When prompted for a user, you can type (parts of) the user name or
       card number.  When prompted for a product, you can type (parts of) the
       product name or barcode.

       About payment and "credit": When paying for something, use either
       Dibbler or the good old money box -- never both at the same time.
       Dibbler keeps track of a "credit" for each user, which is the amount
       of money PVVVV owes the user.  This value decreases with the
       appropriate amount when you register a purchase, and you may increase
       it by putting money in the box and using the "Adjust credit" menu.
       '''

    def local_help(self):
        if self.help_text is None:
            print 'no help here'
        else:
            print ''
            print 'Help for %s:' % (self.header_format % self.name)
            print self.help_text

    def execute(self, **kwargs):
        self.set_context(None)
        try:
            if self.uses_db and not self.session:
                self.session = Session()
            return self._execute(**kwargs)
        except ExitMenu:
            self.at_exit()
            return None
        finally:
            if self.session is not None:
                self.session.close()
                self.session = None

    def _execute(self, **kwargs):
        line_format = '%' + str(len(str(len(self.items)))) + 'd ) %s'
        while True:
            self.print_header()
            self.set_context(None)
            if len(self.items) == 0:
                self.printc('(empty menu)')
                self.pause()
                return None
            for i in range(len(self.items)):
                self.printc(line_format % (i + 1, self.item_name(i)))
            item_i = self.input_choice(len(self.items), prompt=self.prompt) - 1
            if self.item_is_submenu(item_i):
                self.items[item_i].execute()
            else:
                return self.item_value(item_i)


class Selector(Menu):
    def __init__(self, name, items=None, prompt='select> ', return_index=True, exit_msg=None, exit_confirm_msg=None,
                 help_text=None):
        if items is None:
            items = []
        Menu.__init__(self, name, items, prompt, return_index, exit_msg)
        self.header_format = '%s'

    def print_header(self):
        print self.header_format % self.name

    def local_help(self):
        if self.help_text is None:
            print 'This is a selection menu.  Enter one of the listed numbers, or'
            print '\'exit\' to go out and do something else.'
        else:
            print ''
            print 'Help for selector (%s):' % self.name
            print self.help_text


class ConfirmMenu(Menu):
    def __init__(self, prompt='confirm?', default=None, timeout=0):
        Menu.__init__(self, 'question', prompt=prompt,
                      exit_disallowed_msg='Please answer yes or no')
        self.default = default
        self.timeout = timeout

    def _execute(self):
        options = {True: '[y]/n', False: 'y/[n]', None: 'y/n'}[self.default]
        while True:
            result = self.input_str('%s (%s) ' % (self.prompt, options), timeout=self.timeout)
            result = result.lower().strip()
            if result in ['y', 'yes']:
                return True
            elif result in ['n', 'no']:
                return False
            elif self.default is not None and result == '':
                return self.default
            else:
                print 'Please answer yes or no'


class MessageMenu(Menu):
    def __init__(self, name, message, pause_after_message=True):
        Menu.__init__(self, name)
        self.message = message.strip()
        self.pause_after_message = pause_after_message

    def _execute(self):
        self.print_header()
        print ''
        print self.message
        if self.pause_after_message:
            self.pause()


class FAQMenu(Menu):
    def __init__(self):
        Menu.__init__(self, 'Frequently Asked Questions')
        self.items = [MessageMenu('What is the meaning with this program?',
                                  '''
            We want to avoid keeping lots of cash in PVVVV\'s money box and to
            make it easy to pay for stuff without using money.  (Without using
            money each time, that is.  You do of course have to pay for the things
            you buy eventually).

            Dibbler stores a "credit" amount for each user.  When you register a
            purchase in Dibbler, this amount is decreased.  To increase your
            credit, add money to the money box and use "Adjust credit" to tell
            Dibbler about it.
            '''),
                      MessageMenu('Can I still pay for stuff using cash?',
                                  'Yes.  You can safely ignore this program completely.'),
                      MessageMenu('How do I exit from a submenu/dialog/thing?',
                                  'Type "exit" or C-d.'),
                      MessageMenu('What does "." mean?',
                                  '''
            The "." character, known as "full stop" or "period", is most often
            used to indicate the end of a sentence.

            It is also used by Dibbler to indicate that the program wants you to
            read some text before continuing.  Whenever some output ends with a
            line containing only a period, you should read the lines above and
            then press enter to continue.
                                  '''),
                      MessageMenu('Why is the user interface so terribly unintuitive?',
                                  '''
            Answer #1:  It is not.

            Answer #2:  We are trying to compete with PVV\'s microwave oven in
            userfriendliness.

            Answer #3:  YOU are unintuitive.
            '''),
                      MessageMenu('Why is there no help command?',
                                  'There is.  Have you tried typing "help"?'),
                      MessageMenu('Where are the easter eggs?  I tried saying "moo", but nothing happened.',
                                  'Don\'t say "moo".'),
                      MessageMenu('Why does the program speak English when all the users are Norwegians?',
                                  u'Godt spørsmål.  Det virket sikkert som en god idé der og da.'),
                      MessageMenu('I found a bug; is there a reward?',
                                  '''
            No.

            But if you are certain that it is a bug, not a feature, then you
            should fix it (or better: force someone else to do it).

            Follow this procedure:

            1. Check out the Dibbler code from https://dev.pvv.ntnu.no/svn/dibbler

            2. Fix the bug.

            3. Check that the program still runs (and, preferably, that the bug is
               in fact fixed).

            4. Commit.

            5. Update the running copy from svn:

                $ su -
                # su -l -s /bin/bash pvvvv
                $ cd dibbler
                $ svn up

            6. Type "restart" in Dibbler to replace the running process by a new
               one using the updated files.
            '''),
                      MessageMenu('My question isn\'t listed here; what do I do?',
                                  '''
            DON\'T PANIC.

            Follow this procedure:

            1. Ask someone (or read the source code) and get an answer.

            2. Check out the Dibbler code from https://dev.pvv.ntnu.no/svn/dibbler

            3. Add your question (with answer) to the FAQ and commit.

            4. Update the running copy from svn:

                $ su -
                # su -l -s /bin/bash pvvvv
                $ cd dibbler
                $ svn up

            5. Type "restart" in Dibbler to replace the running process by a new
               one using the updated files.
            ''')]


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

        t1 = Transaction(user1, amount,
                         'transfer to ' + user2.name)
        t2 = Transaction(user2, -amount,
                         'transfer from ' + user1.name)
        t1.perform_transaction()
        t2.perform_transaction()
        self.session.add(t1)
        self.session.add(t2)
        try:
            self.session.commit()
            print 'Transfered %d kr from %s to %s' % (amount, user1, user2)
            print 'User %s\'s credit is now %d kr' % (user1, user1.credit)
            print 'User %s\'s credit is now %d kr' % (user2, user2.credit)
        except sqlalchemy.exc.SQLAlchemyError, e:
            print 'Could not perform transfer: %s' % e
            # self.pause()


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


class ShowUserMenu(Menu):
    def __init__(self):
        Menu.__init__(self, 'Show user', uses_db=True)

    def _execute(self):
        self.print_header()
        user = self.input_user('User name, card number or RFID> ')
        print 'User name: %s' % user.name
        print 'Card number: %s' % user.card
        print 'RFID: %s' % user.rfid
        print 'Credit: %s kr' % user.credit
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
            print 'What what?'

    def print_all_transactions(self, user):
        num_trans = len(user.transactions)
        string = '%s\'s transactions (%d):\n' % (user.name, num_trans)
        for t in user.transactions[::-1]:
            string += ' * %s: %s %d kr, ' % \
                      (t.time.strftime('%Y-%m-%d %H:%M'),
                       {True: 'in', False: 'out'}[t.amount < 0],
                       abs(t.amount))
            if t.purchase:
                string += 'purchase ('
                string += ', '.join(map(lambda e: e.product.name,
                                        t.purchase.entries))
                string += ')'
                if t.penalty > 1:
                    string += ' * %dx penalty applied' % t.penalty
            else:
                string += t.description
            string += '\n'
        less(string)

    def print_transactions(self, user, limit=10):
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
                string += ', '.join(map(lambda e: e.product.name,
                                        t.purchase.entries))
                string += ')'
                if t.penalty > 1:
                    string += ' * %dx penalty applied' % t.penalty
            else:
                string += t.description
            string += '\n'
        less(string)

    def print_purchased_products(self, user):
        products = []
        for ref in user.products:
            product = ref.product
            count = ref.count
            products.append((product, count))
        num_products = len(products)
        if num_products == 0:
            print 'No products purchased yet'
        else:
            text = ''
            text += 'Products purchased:\n'
            for product, count in products:
                text += u'{0:<47} {1:>3}\n'.format(product.name, count)
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


class BuyMenu(Menu):
    def __init__(self, session=None):
        Menu.__init__(self, 'Buy', uses_db=True)
        if session:
            self.session = session
        self.superfast_mode = False
        self.help_text = '''
Each purchase may contain one or more products and one or more buyers.

Enter products (by name or bar code) and buyers (by name or bar code)
in any order.  The information gathered so far is displayed after each
addition, and you can type 'what' at any time to redisplay it.

When finished, write an empty line to confirm the purchase.
'''

    def credit_check(self, user):
        """

        :param user:
        :type user: User
        :rtype: boolean
        """
        assert isinstance(user, User)

        return user.credit > conf.low_credit_warning_limit

    def low_credit_warning(self, user, timeout=False):
        assert isinstance(user, User)

        print "***********************************************************************"
        print "***********************************************************************"
        print ""
        print "$$\      $$\  $$$$$$\  $$$$$$$\  $$\   $$\ $$$$$$\ $$\   $$\  $$$$$$\\"
        print "$$ | $\  $$ |$$  __$$\ $$  __$$\ $$$\  $$ |\_$$  _|$$$\  $$ |$$  __$$\\"
        print "$$ |$$$\ $$ |$$ /  $$ |$$ |  $$ |$$$$\ $$ |  $$ |  $$$$\ $$ |$$ /  \__|"
        print "$$ $$ $$\$$ |$$$$$$$$ |$$$$$$$  |$$ $$\$$ |  $$ |  $$ $$\$$ |$$ |$$$$\\"
        print "$$$$  _$$$$ |$$  __$$ |$$  __$$< $$ \$$$$ |  $$ |  $$ \$$$$ |$$ |\_$$ |"
        print "$$$  / \$$$ |$$ |  $$ |$$ |  $$ |$$ |\$$$ |  $$ |  $$ |\$$$ |$$ |  $$ |"
        print "$$  /   \$$ |$$ |  $$ |$$ |  $$ |$$ | \$$ |$$$$$$\ $$ | \$$ |\$$$$$$  |"
        print "\__/     \__|\__|  \__|\__|  \__|\__|  \__|\______|\__|  \__| \______/"
        print ""
        print "***********************************************************************"
        print "***********************************************************************"
        print ""
        print "USER %s HAS LOWER CREDIT THAN %d." % (user.name, conf.low_credit_warning_limit)
        print "THIS PURCHASE WILL CHARGE YOUR CREDIT TWICE AS MUCH."
        print "CONSIDER PUTTING MONEY IN THE BOX TO AVOID THIS."
        print ""
        print "Do you want to continue with this purchase?"

        if timeout:
            print"THIS PURCHASE WILL AUTOMATICALLY BE PERFORMED IN 3 MINUTES!"
            return self.confirm(prompt=">", default=True, timeout=180)
        else:
            return self.confirm(prompt=">", default=True)

    def add_thing_to_purchase(self, thing):
        if isinstance(thing, User):
            if thing.is_anonymous():
                print '--------------------------------------------'
                print'You are now purchasing as the user anonym.'
                print'You have to put money in the anonym-jar.'
                print '--------------------------------------------'

            if not self.credit_check(thing):
                if self.low_credit_warning(user=thing, timeout=self.superfast_mode):
                    Transaction(thing, purchase=self.purchase, penalty=2)
                else:
                    return False
            else:
                Transaction(thing, purchase=self.purchase)
        elif isinstance(thing, Product):
            PurchaseEntry(self.purchase, thing, 1)
        return True

    def _execute(self, initial_contents=None):
        self.print_header()
        self.purchase = Purchase()
        self.exit_confirm_msg = None
        self.superfast_mode = False

        if initial_contents is None:
            initial_contents = []

        for thing in initial_contents:
            self.add_thing_to_purchase(thing)

        isproduct = lambda t: isinstance(t, Product)
        if len(initial_contents) > 0 and all(map(isproduct, initial_contents)):
            self.superfast_mode = True
            print '***********************************************'
            print '****** Buy menu is in SUPERFASTmode[tm]! ******'
            print '*** The purchase will be stored immediately ***'
            print '*** when you enter a user.                  ***'
            print '***********************************************'

        while True:
            self.print_purchase()
            self.printc({(False, False): 'Enter user or product identification',
                         (False, True): 'Enter user identification or more products',
                         (True, False): 'Enter product identification or more users',
                         (True, True): 'Enter more products or users, or an empty line to confirm'
                         }[(len(self.purchase.transactions) > 0,
                            len(self.purchase.entries) > 0)])

            # Read in a 'thing' (product or user):
            thing = self.input_thing(add_nonexisting=('user',),
                                     empty_input_permitted=True,
                                     find_hidden_products=False)

            # Possibly exit from the menu:
            if thing is None:
                if not self.complete_input():
                    if self.confirm('Not enough information entered.  Abort purchase?',
                                    default=True):
                        return False
                    continue
                break
            else:
                # once we get something in the
                # purchase, we want to protect the
                # user from accidentally killing it
                self.exit_confirm_msg = 'Abort purchase?'

            # Add the thing to our purchase object:
            if not self.add_thing_to_purchase(thing):
                continue

            # In superfast mode, we complete the purchase once we get a user:
            if self.superfast_mode and isinstance(thing, User):
                break

        self.purchase.perform_purchase()
        self.session.add(self.purchase)
        try:
            self.session.commit()
        except sqlalchemy.exc.SQLAlchemyError, e:
            print 'Could not store purchase: %s' % e
        else:
            print 'Purchase stored.'
            self.print_purchase()
            for t in self.purchase.transactions:
                if not t.user.is_anonymous():
                    print 'User %s\'s credit is now %d kr' % (t.user.name, t.user.credit)
                    if t.user.credit < conf.low_credit_warning_limit:
                        print 'USER %s HAS LOWER CREDIT THAN %d, AND SHOULD CONSIDER PUTTING SOME MONEY IN THE BOX.'\
                              % (t.user.name, conf.low_credit_warning_limit)
        # skriver til log
        # print Product.price
        # with open("dibbler-out.txt", "a") as f:
        #		f.write("purchase|"+ time() +"|"+self.purchase.entries[0].product.name+"|"+t.user.name+"|+str(Product.price)+|"+'-1'+"|\n")

        return True

    def complete_input(self):
        return self.purchase.is_complete()

    def format_purchase(self):
        self.purchase.set_price()
        transactions = self.purchase.transactions
        entries = self.purchase.entries
        if len(transactions) == 0 and len(entries) == 0:
            return None
        string = 'Purchase:'
        string += '\n buyers: '
        if len(transactions) == 0:
            string += '(empty)'
        else:
            string += ', '.join(
                map(lambda t: t.user.name + ("*" if t.user.credit < conf.user_recent_transaction_limit else ""),
                    transactions))
        string += '\n products: '
        if len(entries) == 0:
            string += '(empty)'
        else:
            string += ', '.join(map(lambda e: '%s (%d kr)' % (e.product.name, e.product.price),
                                    entries))
        if len(transactions) > 1:
            string += '\n price per person: %d kr' % self.purchase.price_per_transaction()
            if any(t.penalty > 1 for t in transactions):
                string += ' *(%d kr)' % (self.purchase.price_per_transaction() * 2)

        string += '\n total price: %d kr' % self.purchase.price

        if any(t.penalty > 1 for t in transactions):
            string += '\n *total with penalty: %d kr' % sum(
                self.purchase.price_per_transaction() * t.penalty for t in transactions)

        return string

    def print_purchase(self):
        info = self.format_purchase()
        if info is not None:
            self.set_context(info)


class AdjustStockMenu(Menu):
    def __init__(self):
        Menu.__init__(self, 'Adjust stock', uses_db=True)

    def _execute(self):
        self.print_header()
        product = self.input_product('Product> ')

        print 'The stock of this product is: %d ' % (product.stock)
        print 'Write the number of products you have added to the stock'
        print 'Alternatively, correct the stock for any mistakes'
        add_stock = self.input_int('Added stock> ', (-1000, 1000))
        print 'You added %d to the stock of %s' % (add_stock, product)

        product.stock += add_stock

        print 'The stock is now %d' % (product.stock)

        try:
            self.session.commit()
            print 'Stock is now stored'
            self.pause()
        except sqlalchemy.exc.SQLAlchemyError, e:
            print 'Could not store stock: %s' % (e)
            self.pause()
            return
        print 'The stock is now %d' % (product.stock)


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
            print 'Could not store stock: %s' % (e)
            self.pause()
            return

        for p in changed_products:
            print p[0].name, ".", p[1], "->", p[0].stock


class AdjustCreditMenu(Menu):  # reimplements ChargeMenu; these should be combined to one
    def __init__(self):
        Menu.__init__(self, 'Adjust credit', uses_db=True)

    def _execute(self):
        self.print_header()
        user = self.input_user('User> ')
        print 'User %s\'s credit is %d kr' % (user.name, user.credit)
        self.set_context('Adjusting credit for user %s' % user.name, display=False)
        print '(Note on sign convention: Enter a positive amount here if you have'
        print 'added money to the PVVVV money box, a negative amount if you have'
        print 'taken money from it)'
        amount = self.input_int('Add amount> ', (-100000, 100000))
        print '(The "log message" will show up in the transaction history in the'
        print '"Show user" menu.  It is not necessary to enter a message, but it'
        print 'might be useful to help you remember why you adjusted the credit)'
        description = self.input_str('Log message> ', length_range=(0, 50))
        if description == '':
            description = 'manually adjusted credit'
        transaction = Transaction(user, -amount, description)
        transaction.perform_transaction()
        self.session.add(transaction)
        try:
            self.session.commit()
            print 'User %s\'s credit is now %d kr' % (user.name, user.credit)
        except sqlalchemy.exc.SQLAlchemyError, e:
            print 'Could not store transaction: %s' % e
            # self.pause()


class ProductListMenu(Menu):
    def __init__(self):
        Menu.__init__(self, 'Product list', uses_db=True)

    def _execute(self):
        self.print_header()
        text = ''
        product_list = self.session.query(Product).filter(Product.hidden == False).order_by(Product.stock.desc())
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
        print 'Result: %s, price: %d kr, bar code: %s, stock: %d, hidden: %s' % (product.name, product.price,
                                                                           product.bar_code, product.stock,
                                                                           ("Y" if product.hidden else "N"))
        # self.pause()


class ProductPopularityMenu(Menu):
    def __init__(self):
        Menu.__init__(self, 'Products by popularity', uses_db=True)

    def _execute(self):
        self.print_header()
        text = ''
        sub = \
            self.session.query(PurchaseEntry.product_id,
                               func.count('*').label('purchase_count')) \
                .group_by(PurchaseEntry.product_id) \
                .subquery()
        product_list = \
            self.session.query(Product, sub.c.purchase_count) \
                .outerjoin((sub, Product.product_id == sub.c.product_id)) \
                .order_by(desc(sub.c.purchase_count)) \
                .filter(sub.c.purchase_count is not None) \
                .all()
        line_format = '%10s | %-' + str(Product.name_length) + 's\n'
        text += line_format % ('items sold', 'product')
        text += '-' * 58 + '\n'
        for product, number in product_list:
            text += line_format % (number, product.name)
        less(text)


class ProductRevenueMenu(Menu):
    def __init__(self):
        Menu.__init__(self, 'Products by revenue', uses_db=True)

    def _execute(self):
        self.print_header()
        text = ''
        sub = \
            self.session.query(PurchaseEntry.product_id,
                               func.count('*').label('purchase_count')) \
                .group_by(PurchaseEntry.product_id) \
                .subquery()
        product_list = \
            self.session.query(Product, sub.c.purchase_count) \
                .outerjoin((sub, Product.product_id == sub.c.product_id)) \
                .order_by(desc(sub.c.purchase_count * Product.price)) \
                .filter(sub.c.purchase_count is not None) \
                .all()
        line_format = '%7s | %10s | %5s | %-' + str(Product.name_length) + 's\n'
        text += line_format % ('revenue', 'items sold', 'price', 'product')
        text += '-' * (31 + Product.name_length) + '\n'
        for product, number in product_list:
            text += line_format % (number * product.price, number, product.price, product.name)
        less(text)


class BalanceMenu(Menu):
    def __init__(self):
        Menu.__init__(self, 'Total balance of PVVVV', uses_db=True)

    def _execute(self):
        self.print_header()
        text = ''
        total_value = 0
        product_list = self.session.query(Product).all()
        for p in product_list:
            total_value += p.stock * p.price

        total_credit = self.session.query(sqlalchemy.func.sum(User.credit)).first()[0]
        total_balance = total_value - total_credit

        line_format = '%15s | %5d \n'
        text += line_format % ('Total value', total_value)
        text += 24 * '-' + '\n'
        text += line_format % ('Total credit', total_credit)
        text += 24 * '-' + '\n'
        text += line_format % ('Total balance', total_balance)
        less(text)


class LoggedStatisticsMenu(Menu):
    def __init__(self):
        Menu.__init__(self, 'Statistics from log', uses_db=True)

    def _execute(self):
        statisticsTextOnly()


def restart():
    # Does not work if the script is not executable, or if it was
    # started by searching $PATH.
    os.execv(sys.argv[0], sys.argv)


if not conf.stop_allowed:
    signal.signal(signal.SIGQUIT, signal.SIG_IGN)

if not conf.stop_allowed:
    signal.signal(signal.SIGTSTP, signal.SIG_IGN)


class MainMenu(Menu):
    def special_input_choice(self, in_str):
        buy_menu = BuyMenu(Session())
        thing = buy_menu.search_for_thing(in_str)
        if thing:
            buy_menu.execute(initialContents=[thing])
            print self.show_context()
            return True
        return False

    def invalid_menu_choice(self, in_str):
        print self.show_context()


class AddStockMenu(Menu):
    def __init__(self):
        Menu.__init__(self, 'Add stock and adjust credit', uses_db=True)
        self.help_text = '''
Enter what you have bought for PVVVV here, along with your user name and how
much money you're due in credits for the purchase when prompted.
		'''

    def _execute(self):
        questions = {
            (False, False): 'Enter user id or a string of the form "<number> <product>"',
            (False, True): 'Enter user id or more strings of the form "<number> <product>"',
            (True, False): 'Enter a string of the form "<number> <product>"',
            (True, True): 'Enter more strings of the form "<number> <product>", or an empty line to confirm'
        }

        self.user = None
        self.products = {}
        self.price = 0

        while True:
            self.print_info()
            self.printc(questions[bool(self.user), bool(len(self.products))])
            thing_price = 0

            # Read in a 'thing' (product or user):
            line = self.input_multiple(add_nonexisting=('user', 'product'), empty_input_permitted=True,
                                       find_hidden_products=False)

            if line:
                (thing, amount) = line

                if isinstance(thing, Product):
                    self.printc("%d of %s registered" % (amount, thing.name))
                    thing_price = self.input_int('What did you pay a piece? ', (1, 100000),
                                                 default=thing.price) * amount
                    self.price += thing_price

                # once we get something in the
                # purchase, we want to protect the
                # user from accidentally killing it
                self.exit_confirm_msg = 'Abort transaction?'
            else:
                thing = None

                if not self.complete_input():
                    if self.confirm('Not enough information entered. Abort transaction?', default=True):
                        return False
                    continue

                break

            # Add the thing to the pending adjustments:
            self.add_thing_to_pending(thing, amount, thing_price)

        if self.confirm('Do you want to change the credited amount?', default=False):
            self.price = self.input_int('Total amount> ', (1, 100000), default=self.price)

        self.perform_transaction()

    def complete_input(self):
        return (bool(self.user) and len(self.products) and self.price)

    def print_info(self):
        print(6 + Product.name_length) * '-'
        if self.price:
            print("Amount to be credited: %" + str(Product.name_length - 17) + "i") % (self.price)
        if self.user:
            print("User to credit: %" + str(Product.name_length - 10) + "s") % (self.user.name)
        print('\n%-' + str(Product.name_length - 1) + 's Amount') % ("Product")
        print(6 + Product.name_length) * '-'
        if len(self.products):
            # print "Products added:"
            # print (6+Product.name_length)*'-'
            for product in self.products.keys():
                print('%' + str(-Product.name_length) + 's %5i') % (product.name, self.products[product][0])
                print(6 + Product.name_length) * '-'

    def add_thing_to_pending(self, thing, amount, price):
        if isinstance(thing, User):
            if self.user:
                print "Only one user may be credited for a purchase, transfer credit manually afterwards"
                return
            else:
                self.user = thing
        elif thing in self.products.keys():
            print 'Already added this product, adding amounts'
            self.products[thing][0] += amount
            self.products[thing][1] += price
        else:
            self.products[thing] = [amount, price]

    def perform_transaction(self):
        # self.user.credit += self.price
        description = self.input_str('Log message> ', length_range=(0, 50))
        if description == '':
            description = 'Purchased products for PVVVV, adjusted credit ' + str(self.price)
        transaction = Transaction(self.user, -self.price, description)
        transaction.perform_transaction()
        self.session.add(transaction)
        for product in self.products:
            value = max(product.stock, 0) * product.price + self.products[product][1]
            old_price = product.price
            old_hidden = product.hidden
            product.price = int(ceil(float(value) / (max(product.stock, 0) + self.products[product][0])))
            product.stock += self.products[product][0]
            product.hidden = False
            print "New stock for %s: %d" % (product.name, product.stock), \
                ("- New price: " + str(product.price) if old_price != product.price else ""), \
                ("- Removed hidden status" if old_hidden != product.hidden else "")
        try:
            self.session.commit()
            print "Success! Transaction performed:"
            # self.print_info()
            print "User %s's credit is now %i" % (self.user.name, self.user.credit)
        except sqlalchemy.exc.SQLAlchemyError, e:
            print 'Could not perform transaction: %s' % e


main = MainMenu('Dibbler main menu',
                items=[BuyMenu(),
                       ProductListMenu(),
                       ShowUserMenu(),
                       UserListMenu(),
                       AdjustCreditMenu(),
                       TransferMenu(),
                       AddStockMenu(),
                       Menu('Add/edit',
                            items=[AddUserMenu(),
                                   EditUserMenu(),
                                   AddProductMenu(),
                                   EditProductMenu(),
                                   AdjustStockMenu(),
                                   CleanupStockMenu(), ]),
                       ProductSearchMenu(),
                       Menu('Statistics',
                            items=[ProductPopularityMenu(),
                                   ProductRevenueMenu(),
                                   BalanceMenu(),
                                   LoggedStatisticsMenu()]),
                       FAQMenu()
                       ],
                exit_msg='happy happy joy joy',
                exit_confirm_msg='Really quit Dibbler?')
if not conf.quit_allowed:
    main.exit_disallowed_msg = 'You can check out any time you like, but you can never leave.'
while True:
    try:
        main.execute()
    except KeyboardInterrupt:
        print ''
        print 'Interrupted.'
    except:
        print 'Something went wrong.'
        print '%s: %s' % sys.exc_info()[0], sys.exc_info()[1]
        if conf.show_tracebacks:
            traceback.print_tb(sys.exc_info()[2])
    else:
        break
    print 'Restarting main menu.'

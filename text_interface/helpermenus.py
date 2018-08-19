# -*- coding: utf-8 -*-


import os
import random
import re
import sys
from select import select

import conf
from db import User, Session
from helpers import search_user, search_product, safe_str, guess_data_type, argmax
from text_interface import context_commands, local_help_commands, help_commands, \
    exit_commands


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
            print(self.exit_disallowed_msg)
            return
        if self.exit_confirm_msg is not None:
            if not self.confirm(self.exit_confirm_msg, default=True):
                return
        raise ExitMenu()

    def at_exit(self):
        if self.exit_msg:
            print(self.exit_msg)

    def set_context(self, string, display=True):
        self.context = string
        if self.context is not None and display:
            print(self.context)

    def add_to_context(self, string):
        self.context += string

    def printc(self, string):
        print(string)
        if self.context is None:
            self.context = string
        else:
            self.context += '\n' + string

    def show_context(self):
        print(self.header_format % self.name)
        if self.context is not None:
            print(self.context)

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
                    print('Value must match regular expression "%s"' % regex)
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
                        print('Value must have length in range [%d,%d]' % length_range)
                    elif length_range[0]:
                        print('Value must have length at least %d' % length_range[0])
                    else:
                        print('Value must have length at most %d' % length_range[1])
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
                        result = str(input(), conf.input_encoding).strip()
                else:
                    result = str(input(safe_str(prompt)), conf.input_encoding).strip()
            except EOFError:
                print('quit')
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
                continue
            if self.special_input_options(result):
                continue
            if empty_string_is_none and result == '':
                return None
            return result

    def special_input_options(self, result):
        """
        Handles special, magic input for input_str

        Override this in subclasses to implement magic menu
        choices.  Return True if str was some valid magic menu
        choice, False otherwise.
        """
        return False

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
                print('Please enter something')
            # 'c' in main menu to change colours
            elif result == 'c':
                os.system('echo -e "\033[' + str(random.randint(40, 49)) + ';' + str(random.randint(30, 37)) + ';5m"')
                os.system('clear')
                self.show_context()

            # 'cs' in main menu to change colours back to default
            elif result == 'cs':
                os.system('echo -e "\033[0m"')
                os.system('clear')
                self.show_context()

            else:
                if result.isdigit():
                    choice = int(result)
                    if choice == 0 and 10 <= number_of_choices:
                        return 10
                    if 0 < choice <= number_of_choices:
                        return choice
                if not self.special_input_choice(result):
                    self.invalid_menu_choice(result)

    def invalid_menu_choice(self, in_str):
        print('Please enter a valid choice.')

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
                        print('Value must be in range [%d,%d]' % allowed_range)
                    elif allowed_range[0]:
                        print('Value must be at least %d' % allowed_range[0])
                    else:
                        print('Value must be at most %d' % allowed_range[1])
                else:
                    return value
            except ValueError:
                print("Please enter an integer")

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
                    print('Interpreting input as "<number> <product>"')
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
                         add_non_existing=(), find_hidden_products=True):
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
            if type_guess is not None and thing_for_type[type_guess] in add_non_existing:
                return self.search_add(search_str)
            # print 'No match found for "%s".' % search_str
            return None
        return self.search_ui2(search_str, results[selected_thing], selected_thing)

    @staticmethod
    def search_result_value(result):
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
            print('"%s" looks like a username, but no such user exists.' % string)
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
                print('Card number of %s set to %s (was %s)' % (user.name, string, old_card))
                return user
            return None
        if type_guess == 'bar_code':
            print('"%s" looks like the bar code for a product, but no such product exists.' % string)
            return None

    def search_ui(self, search_fun, search_str, thing):
        result = search_fun(search_str, self.session)
        return self.search_ui2(search_str, result, thing)

    def search_ui2(self, search_str, result, thing):
        if not isinstance(result, list):
            return result
        if len(result) == 0:
            print('No %ss matching "%s"' % (thing, search_str))
            return None
        if len(result) == 1:
            msg = 'One %s matching "%s": %s.  Use this?' % \
                  (thing, search_str, str(result[0]))
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

    @staticmethod
    def confirm(prompt, default=None, timeout=None):
        return ConfirmMenu(prompt, default, timeout).execute()

    def print_header(self):
        print("")
        print(self.header_format % self.name)

    def pause(self):
        self.input_str('.')

    @staticmethod
    def general_help():
        print('''
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
       ''')

    def local_help(self):
        if self.help_text is None:
            print('no help here')
        else:
            print('')
            print('Help for %s:' % (self.header_format % self.name))
            print(self.help_text)

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


class MessageMenu(Menu):
    def __init__(self, name, message, pause_after_message=True):
        Menu.__init__(self, name)
        self.message = message.strip()
        self.pause_after_message = pause_after_message

    def _execute(self):
        self.print_header()
        print('')
        print(self.message)
        if self.pause_after_message:
            self.pause()


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
                print('Please answer yes or no')


class Selector(Menu):
    def __init__(self, name, items=None, prompt='select> ', return_index=True, exit_msg=None, exit_confirm_msg=None,
                 help_text=None):
        if items is None:
            items = []
        Menu.__init__(self, name, items, prompt, return_index, exit_msg)
        self.header_format = '%s'

    def print_header(self):
        print(self.header_format % self.name)

    def local_help(self):
        if self.help_text is None:
            print('This is a selection menu.  Enter one of the listed numbers, or')
            print('\'exit\' to go out and do something else.')
        else:
            print('')
            print('Help for selector (%s):' % self.name)
            print(self.help_text)

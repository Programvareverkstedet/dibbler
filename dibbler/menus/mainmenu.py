
# -*- coding: utf-8 -*-
import os
import random
import sys

from dibbler.db import Session

from . import faq_commands, restart_commands
from .buymenu import BuyMenu
from .faq import FAQMenu
from .helpermenus import Menu


def restart():
    # Does not work if the script is not executable, or if it was
    # started by searching $PATH.
    os.execv(sys.argv[0], sys.argv)


class MainMenu(Menu):
    def special_input_choice(self, in_str):
        mv = in_str.split()
        if len(mv) == 2 and mv[0].isdigit():
            num = int(mv[0])
            item_name = mv[1]
        else:
            num = 1
            item_name = in_str
        buy_menu = BuyMenu(Session())
        thing = buy_menu.search_for_thing(item_name, find_hidden_products=False)
        if thing:
            buy_menu.execute(initial_contents=[(thing, num)])
            self.show_context()
            return True
        return False

    def special_input_options(self, result):
        if result in faq_commands:
            FAQMenu().execute()
            return True
        if result in restart_commands:
            if self.confirm('Restart Dibbler?'):
                restart()
                pass
            return True
        elif result == 'c':
            os.system('echo -e "\033[' + str(random.randint(40, 49)) + ';' + str(random.randint(30, 37)) + ';5m"')
            os.system('clear')
            self.show_context()
            return True
        elif result == 'cs':
            os.system('echo -e "\033[0m"')
            os.system('clear')
            self.show_context()
            return True
        return False

    def invalid_menu_choice(self, in_str):
        print(self.show_context())

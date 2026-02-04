import os
import random
import sys

from sqlalchemy.orm import Session

from .buymenu import BuyMenu
from .faq import FAQMenu
from .helpermenus import Menu

faq_commands = ["faq"]
restart_commands = ["restart"]


def restart():
    # Does not work if the script is not executable, or if it was
    # started by searching $PATH.
    os.execv(sys.argv[0], sys.argv)


class MainMenu(Menu):
    def __init__(self, sql_session: Session, **kwargs):
        super().__init__("Dibbler main menu", sql_session, **kwargs)

    def special_input_choice(self, in_str: str) -> bool:
        mv = in_str.split()
        if len(mv) == 2 and mv[0].isdigit():
            num = int(mv[0])
            item_name = mv[1]
        else:
            num = 1
            item_name = in_str
        buy_menu = BuyMenu(self.sql_session)
        thing = buy_menu.search_for_thing(item_name, find_hidden_products=False)
        if thing:
            buy_menu.execute(initial_contents=[(thing, num)])
            self.show_context()
            return True
        return False

    def special_input_options(self, result: str) -> bool:
        if result in faq_commands:
            FAQMenu(self.sql_session).execute()
            return True
        if result in restart_commands:
            if self.confirm("Restart Dibbler?"):
                restart()
                pass
            return True
        if result == "c":
            print(f"\033[{random.randint(40, 49)};{random.randint(30, 37)};5m")
            print("\033[2J")
            self.show_context()
            return True
        if result == "cs":
            print("\033[0m")
            print("\033[2J")
            self.show_context()
            return True
        return False

    def invalid_menu_choice(self, in_str: str) -> None:
        print(self.show_context())

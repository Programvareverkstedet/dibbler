#!/usr/bin/python
# -*- coding: utf-8 -*-

import random
import sys
import traceback

from .helpers import *
from .menus.addstock import AddStockMenu
from .menus.buymenu import BuyMenu
from .menus.editing import *
from .menus.faq import FAQMenu
from .menus.helpermenus import Menu
from .menus.mainmenu import MainMenu

from .menus.miscmenus import (
    ProductSearchMenu,
    TransferMenu,
    AdjustCreditMenu,
    UserListMenu,
    ShowUserMenu,
    ProductListMenu,
)

from .menus.printermenu import PrintLabelMenu
from .menus.stats import *

from .conf import config

random.seed()

def main():
    if not config.getboolean('general', 'stop_allowed'):
        signal.signal(signal.SIGQUIT, signal.SIG_IGN)

    if not config.getboolean('general', 'stop_allowed'):
        signal.signal(signal.SIGTSTP, signal.SIG_IGN)

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
                           FAQMenu(),
                           PrintLabelMenu()
                           ],
                    exit_msg='happy happy joy joy',
                    exit_confirm_msg='Really quit Dibbler?')
    if not config.getboolean('general', 'quit_allowed'):
        main.exit_disallowed_msg = 'You can check out any time you like, but you can never leave.'
    while True:
        # noinspection PyBroadException
        try:
            main.execute()
        except KeyboardInterrupt:
            print('')
            print('Interrupted.')
        except:
            print('Something went wrong.')
            print(f'{sys.exc_info()[0]}: {sys.exc_info()[1]}')
            if config.getboolean('general', 'show_tracebacks'):
                traceback.print_tb(sys.exc_info()[2])
        else:
            break
        print('Restarting main menu.')


if __name__ == '__main__':
  main()
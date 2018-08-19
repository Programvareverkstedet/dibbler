#!/usr/bin/python
# -*- coding: utf-8 -*-

import random
import sys
import traceback

from helpers import *
from text_interface.addstock import AddStockMenu
from text_interface.buymenu import BuyMenu
from text_interface.editing import *
from text_interface.faq import FAQMenu
from text_interface.helpermenus import Menu
from text_interface.mainmenu import MainMenu
from text_interface.miscmenus import ProductSearchMenu, TransferMenu, AdjustCreditMenu, UserListMenu, ShowUserMenu, \
    ProductListMenu
from text_interface.printermenu import PrintLabelMenu
from text_interface.stats import *

random.seed()


if __name__ == '__main__':
    if not conf.stop_allowed:
        signal.signal(signal.SIGQUIT, signal.SIG_IGN)

    if not conf.stop_allowed:
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
    if not conf.quit_allowed:
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
            print('%s: %s' % (sys.exc_info()[0], sys.exc_info()[1]))
            if conf.show_tracebacks:
                traceback.print_tb(sys.exc_info()[2])
        else:
            break
        print('Restarting main menu.')

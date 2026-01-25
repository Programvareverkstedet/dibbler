#!/usr/bin/python
# -*- coding: utf-8 -*-

import random
import sys
import traceback

from ..conf import config
from ..lib.helpers import *
from ..menus import *

random.seed()


def main():
    if not config["general"]["stop_allowed"]:
        signal.signal(signal.SIGQUIT, signal.SIG_IGN)

    if not config["general"]["stop_allowed"]:
        signal.signal(signal.SIGTSTP, signal.SIG_IGN)

    main = MainMenu(
        "Dibbler main menu",
        items=[
            BuyMenu(),
            ProductListMenu(),
            ShowUserMenu(),
            UserListMenu(),
            AdjustCreditMenu(),
            TransferMenu(),
            AddStockMenu(),
            Menu(
                "Add/edit",
                items=[
                    AddUserMenu(),
                    EditUserMenu(),
                    AddProductMenu(),
                    EditProductMenu(),
                    AdjustStockMenu(),
                    CleanupStockMenu(),
                ],
            ),
            ProductSearchMenu(),
            Menu(
                "Statistics",
                items=[
                    ProductPopularityMenu(),
                    ProductRevenueMenu(),
                    BalanceMenu(),
                    LoggedStatisticsMenu(),
                ],
            ),
            FAQMenu(),
            PrintLabelMenu(),
        ],
        exit_msg="happy happy joy joy",
        exit_confirm_msg="Really quit Dibbler?",
    )
    if not config["general"]["quit_allowed"]:
        main.exit_disallowed_msg = "You can check out any time you like, but you can never leave."
    while True:
        # noinspection PyBroadException
        try:
            main.execute()
        except KeyboardInterrupt:
            print("")
            print("Interrupted.")
        except:
            print("Something went wrong.")
            print(f"{sys.exc_info()[0]}: {sys.exc_info()[1]}")
            if config["general"]["show_tracebacks"]:
                traceback.print_tb(sys.exc_info()[2])
        else:
            break
        print("Restarting main menu.")


if __name__ == "__main__":
    main()

#!/usr/bin/python

import random
import sys
import traceback
from signal import (
    SIG_IGN,
    SIGQUIT,
    SIGTSTP,
)
from signal import (
    signal as set_signal_handler,
)

from sqlalchemy.orm import Session

from ..conf import config
from ..menus import (
    AddProductMenu,
    AddStockMenu,
    AddUserMenu,
    AdjustCreditMenu,
    AdjustStockMenu,
    BalanceMenu,
    BuyMenu,
    CleanupStockMenu,
    EditProductMenu,
    EditUserMenu,
    FAQMenu,
    LoggedStatisticsMenu,
    MainMenu,
    Menu,
    PrintLabelMenu,
    ProductListMenu,
    ProductPopularityMenu,
    ProductRevenueMenu,
    ProductSearchMenu,
    ShowUserMenu,
    TransferMenu,
    UserListMenu,
)

random.seed()


def main(sql_session: Session):
    if not config["general"]["stop_allowed"]:
        set_signal_handler(SIGQUIT, SIG_IGN)

    if not config["general"]["stop_allowed"]:
        set_signal_handler(SIGTSTP, SIG_IGN)

    main_menu = MainMenu(
        sql_session,
        items=[
            BuyMenu(sql_session),
            ProductListMenu(sql_session),
            ShowUserMenu(sql_session),
            UserListMenu(sql_session),
            AdjustCreditMenu(sql_session),
            TransferMenu(sql_session),
            AddStockMenu(sql_session),
            Menu(
                "Add/edit",
                sql_session,
                items=[
                    AddUserMenu(sql_session),
                    EditUserMenu(sql_session),
                    AddProductMenu(sql_session),
                    EditProductMenu(sql_session),
                    AdjustStockMenu(sql_session),
                    CleanupStockMenu(sql_session),
                ],
            ),
            ProductSearchMenu(sql_session),
            Menu(
                "Statistics",
                sql_session,
                items=[
                    ProductPopularityMenu(sql_session),
                    ProductRevenueMenu(sql_session),
                    BalanceMenu(sql_session),
                    LoggedStatisticsMenu(sql_session),
                ],
            ),
            FAQMenu(sql_session),
            PrintLabelMenu(sql_session),
        ],
        exit_msg="happy happy joy joy",
        exit_confirm_msg="Really quit Dibbler?",
    )
    if not config["general"]["quit_allowed"]:
        main_menu.exit_disallowed_msg = (
            "You can check out any time you like, but you can never leave."
        )
    while True:
        # noinspection PyBroadException
        try:
            main_menu.execute()
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

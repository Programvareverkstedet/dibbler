# -*- coding: utf-8 -*-

from .addstock import AddStockMenu
from .buymenu import BuyMenu
from .editing import (
    AddUserMenu,
    EditUserMenu,
    AddProductMenu,
    EditProductMenu,
    AdjustStockMenu,
    CleanupStockMenu,
)
from .faq import FAQMenu
from .helpermenus import Menu
from .mainmenu import MainMenu
from .miscmenus import (
    ProductSearchMenu,
    TransferMenu,
    AdjustCreditMenu,
    UserListMenu,
    ShowUserMenu,
    ProductListMenu,
)
from .printermenu import PrintLabelMenu
from .stats import (
  ProductPopularityMenu,
  ProductRevenueMenu,
  BalanceMenu,
  LoggedStatisticsMenu
)

exit_commands = ['exit', 'abort', 'quit', 'bye', 'eat flaming death', 'q']
help_commands = ['help', '?']
context_commands = ['what', '??']
local_help_commands = ['help!', '???']
faq_commands = ['faq']
restart_commands = ['restart']
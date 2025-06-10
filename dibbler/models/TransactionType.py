from enum import Enum


class TransactionType(Enum):
    """
    Enum for transaction types.
    """

    ADJUST_BALANCE = "adjust_balance"
    ADJUST_STOCK = "adjust_stock"
    TRANSFER = "transfer"
    ADD_PRODUCT = "add_product"
    BUY_PRODUCT = "buy_product"

from enum import Enum


class TransactionType(Enum):
    """
    Enum for transaction types.
    """

    ADD_PRODUCT = "add_product"
    ADJUST_BALANCE = "adjust_balance"
    ADJUST_INTEREST = "adjust_interest"
    ADJUST_PENALTY = "adjust_penalty"
    ADJUST_STOCK = "adjust_stock"
    BUY_PRODUCT = "buy_product"
    TRANSFER = "transfer"

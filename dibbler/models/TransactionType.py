
from sqlalchemy.sql.sqltypes import Enum


class TransactionType(Enum):
    """
    Enum for transaction types.
    """
    ADJUST = "adjust"
    TRANSFER = "transfer"
    ADD_PRODUCT = "add_product"
    BUY_PRODUCT = "buy_product"

from datetime import datetime

from sqlalchemy.orm import Session

from dibbler.models import (
    Transaction,
    TransactionType,
    User,
    Product,
)

from .product_price import product_price


def buy_product(
    sql_session: Session,
    user: User,
    product: Product,
    product_count: int,
    time: datetime | None = None,
    message: str | None = None,
) -> Transaction:
    """
    Creates a BUY_PRODUCT transaction with the amount automatically calculated based on the product's current price.
    """

    price = product_price(sql_session, product)

    return Transaction(
        time=time,
        type_=TransactionType.BUY_PRODUCT,
        amount=price * product_count,
        user_id=user.id,
        product_id=product.id,
        product_count=product_count,
        message=message,
    )

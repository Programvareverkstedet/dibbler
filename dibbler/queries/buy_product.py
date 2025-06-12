import math
from datetime import datetime

from sqlalchemy.orm import Session

from dibbler.models import (
    Product,
    Transaction,
    User,
)
from dibbler.queries.current_interest import current_interest
from dibbler.queries.current_penalty import current_penalty
from dibbler.queries.user_balance import user_balance

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

    # balance = user_balance(sql_session, user)

    # price = product_price(sql_session, product)

    # interest_rate = current_interest(sql_session)

    # penalty_threshold, penalty_multiplier_percent = current_penalty(sql_session)

    # price *= product_count

    # price *= 1 + interest_rate / 100

    # if balance < penalty_threshold:
    #     price *= 1 + penalty_multiplier_percent / 100

    # price = math.ceil(price)

    return Transaction.buy_product(
        time=time,
        # amount=price,
        user_id=user.id,
        product_id=product.id,
        product_count=product_count,
        message=message,
    )

from datetime import datetime

from sqlalchemy.orm import Session

from dibbler.models import Product, Transaction, User


def buy_product(
    sql_session: Session,
    user: User,
    product: Product,
    product_count: int,
    time: datetime | None = None,
    message: str | None = None,
) -> Transaction:
    if user.id is None:
        raise ValueError("User must be persisted in the database.")

    if product.id is None:
        raise ValueError("Product must be persisted in the database.")

    if product_count <= 0:
        raise ValueError("Product count must be positive.")

    # TODO: verify time is not behind last transaction's time

    transaction = Transaction.buy_product(
        user_id=user.id,
        product_id=product.id,
        product_count=product_count,
        time=time,
        message=message,
    )

    sql_session.add(transaction)
    sql_session.commit()

    return transaction

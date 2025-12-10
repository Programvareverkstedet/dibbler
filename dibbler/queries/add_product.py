from datetime import datetime

from sqlalchemy.orm import Session

from dibbler.models import Product, Transaction, User


def add_product(
    sql_session: Session,
    user: User,
    product: Product,
    amount: int,
    per_product: int,
    product_count: int,
    time: datetime | None = None,
    message: str | None = None,
) -> Transaction:
    if user.id is None:
        raise ValueError("User must be persisted in the database.")

    if product.id is None:
        raise ValueError("Product must be persisted in the database.")

    if amount <= 0:
        raise ValueError("Amount must be positive.")

    if per_product <= 0:
        raise ValueError("Per product price must be positive.")

    if product_count <= 0:
        raise ValueError("Product count must be positive.")

    if per_product * product_count < amount:
        raise ValueError("Total per product price must be at least equal to amount.")

    # TODO: verify time is not behind last transaction's time

    transaction = Transaction.add_product(
        user_id=user.id,
        product_id=product.id,
        amount=amount,
        per_product=per_product,
        product_count=product_count,
        time=time,
        message=message,
    )

    sql_session.add(transaction)
    sql_session.commit()

    return transaction

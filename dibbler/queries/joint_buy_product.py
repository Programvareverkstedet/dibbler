from datetime import datetime

from sqlalchemy.orm import Session

from dibbler.models import (
    Product,
    Transaction,
    User,
)


def joint_buy_product(
    sql_session: Session,
    product: Product,
    product_count: int,
    instigator: User,
    users: list[User],
    time: datetime | None = None,
    message: str | None = None,
) -> None:
    """
    Create buy product transactions for multiple users at once.
    """

    if product.id is None:
        raise ValueError("Product must be persisted in the database.")

    if instigator not in users:
        raise ValueError("Instigator must be in the list of users buying the product.")

    if any(user.id is None for user in users):
        raise ValueError("All users must be persisted in the database.")

    if product_count <= 0:
        raise ValueError("Product count must be positive.")

    joint_transaction = Transaction.joint(
        user_id=instigator.id,
        product_id=product.id,
        product_count=product_count,
        time=time,
        message=message,
    )
    sql_session.add(joint_transaction)
    sql_session.flush()  # Ensure joint_transaction gets an ID

    for user in users:
        buy_transaction = Transaction.joint_buy_product(
            user_id=user.id,
            joint_transaction_id=joint_transaction.id,
            time=time,
            message=message,
        )
        sql_session.add(buy_transaction)

    sql_session.commit()

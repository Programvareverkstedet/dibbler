from datetime import datetime

from sqlalchemy.orm import Session

from dibbler.models import Transaction, User


def adjust_balance(
    sql_session: Session,
    user: User,
    amount: int,
    time: datetime | None = None,
    message: str | None = None,
) -> Transaction:
    if user.id is None:
        raise ValueError("User must be persisted in the database.")

    if amount == 0:
        raise ValueError("Amount must be non-zero.")

    # TODO: verify time is not behind last transaction's time

    transaction = Transaction.adjust_balance(
        user_id=user.id,
        amount=amount,
        time=time,
        message=message,
    )

    sql_session.add(transaction)
    sql_session.commit()

    return transaction

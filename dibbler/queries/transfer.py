from datetime import datetime

from sqlalchemy.orm import Session

from dibbler.models import Transaction, User


def transfer(
    sql_session: Session,
    from_user: User,
    to_user: User,
    amount: int,
    time: datetime | None = None,
    message: str | None = None,
) -> Transaction:
    if from_user.id is None:
        raise ValueError("From user must be persisted in the database.")

    if to_user.id is None:
        raise ValueError("To user must be persisted in the database.")

    if amount <= 0:
        raise ValueError("Amount must be positive.")

    # TODO: verify time is not behind last transaction's time

    transaction = Transaction.transfer(
        user_id=from_user.id,
        transfer_user_id=to_user.id,
        amount=amount,
        time=time,
        message=message,
    )

    sql_session.add(transaction)
    sql_session.commit()

    return transaction

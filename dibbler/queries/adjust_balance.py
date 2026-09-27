from datetime import datetime

from sqlalchemy.orm import Session

from dibbler.models import Transaction, TransactionLog, TransactionLogUser, User
from dibbler.models.enums import TransactionLogEntryType


def adjust_balance(
    sql_session: Session,
    user: User,
    amount: int,
    description: str | None = None,
) -> Transaction:
    if amount == 0:
        raise ValueError("Amount must be non-zero.")

    transaction = Transaction(user, amount, description)
    transaction.perform_transaction()
    sql_session.add(transaction)

    header = TransactionLog(
        type=TransactionLogEntryType.ADJUST_BALANCE,
        time=datetime.now(),
        description=description,
    )
    sql_session.add(header)
    sql_session.add(
        TransactionLogUser(transaction=header, user=user, amount=transaction.amount),
    )
    sql_session.flush()

    return transaction

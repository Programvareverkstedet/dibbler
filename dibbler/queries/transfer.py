from datetime import datetime

from sqlalchemy.orm import Session

from dibbler.models import Transaction, TransactionLog, TransactionLogUser, User
from dibbler.models.enums import TransactionLogEntryType


def transfer(
    sql_session: Session,
    from_user: User,
    to_user: User,
    amount: int,
    comment: str = "",
) -> tuple[Transaction, Transaction]:
    if amount <= 0:
        raise ValueError("Amount must be positive.")

    if from_user == to_user:
        raise ValueError("Cannot transfer to the same user.")

    outgoing = Transaction(from_user, amount, f'transfer to {to_user.name} "{comment}"')
    incoming = Transaction(to_user, -amount, f'transfer from {from_user.name} "{comment}"')
    outgoing.perform_transaction()
    incoming.perform_transaction()
    sql_session.add(outgoing)
    sql_session.add(incoming)

    header = TransactionLog(
        type=TransactionLogEntryType.TRANSFER,
        time=datetime.now(),
        description=comment or None,
    )
    sql_session.add(header)
    sql_session.add_all(
        [
            TransactionLogUser(transaction=header, user=from_user, amount=outgoing.amount),
            TransactionLogUser(transaction=header, user=to_user, amount=incoming.amount),
        ],
    )
    sql_session.flush()

    return outgoing, incoming

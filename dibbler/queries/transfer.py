from datetime import datetime

from sqlalchemy.orm import Session

from dibbler.models import TransactionLog, TransactionLogUser, User
from dibbler.models.enums import TransactionLogEntryType


def transfer(
    sql_session: Session,
    from_user: User,
    to_user: User,
    amount: int,
    comment: str = "",
) -> None:
    if amount <= 0:
        raise ValueError("Amount must be positive.")

    if from_user == to_user:
        raise ValueError("Cannot transfer to the same user.")

    from_user.credit -= amount
    to_user.credit += amount

    header = TransactionLog(
        type=TransactionLogEntryType.TRANSFER,
        time=datetime.now(),
        description=comment or None,
    )
    sql_session.add(header)
    sql_session.add_all(
        [
            TransactionLogUser(transaction=header, user=from_user, amount=amount),
            TransactionLogUser(transaction=header, user=to_user, amount=-amount),
        ],
    )
    sql_session.flush()

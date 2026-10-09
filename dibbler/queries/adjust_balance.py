from datetime import datetime

from sqlalchemy.orm import Session

from dibbler.models import Transaction, TransactionLog, TransactionLogUser, User
from dibbler.models.enums import TransactionLogEntryType

MAX_BALANCE_ADJUSTMENT = 9999


def adjust_balance(
    sql_session: Session,
    user: User,
    amount: int,
    description: str | None = None,
) -> Transaction:
    if amount == 0:
        raise ValueError("Amount must be non-zero.")

    if abs(amount) > MAX_BALANCE_ADJUSTMENT:
        raise ValueError(
            f"Amount must be between {-MAX_BALANCE_ADJUSTMENT} and {MAX_BALANCE_ADJUSTMENT}.",
        )

    # TODO: remove this `min` once we get rid of `Transaction`
    max_description_length = min(Transaction.description_length, TransactionLog.description_length)
    if description is not None and len(description) > max_description_length:
        raise ValueError(f"Description must be at most {max_description_length} characters.")

    user.credit -= amount

    header = TransactionLog(
        type=TransactionLogEntryType.ADJUST_BALANCE,
        time=datetime.now(),
        description=description,
    )
    sql_session.add(header)
    sql_session.add(TransactionLogUser(transaction=header, user=user, amount=amount))

    # NOTE: Only kept around for backwards compatibility until the legacy tables are dropped.
    transaction = Transaction(user, amount, description)
    transaction.time = header.time
    sql_session.add(transaction)
    sql_session.flush()

    return transaction

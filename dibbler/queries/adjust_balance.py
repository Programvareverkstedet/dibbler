from sqlalchemy.orm import Session

from dibbler.models import Transaction, User


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
    sql_session.flush()

    return transaction

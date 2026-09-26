from sqlalchemy.orm import Session

from dibbler.models import Transaction, User


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
    sql_session.flush()

    return outgoing, incoming

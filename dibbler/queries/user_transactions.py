from sqlalchemy import select
from sqlalchemy.orm import Session

from dibbler.models import Transaction, User

# TODO: allow filtering out 'special transactions' like 'ADJUST_INTEREST' and 'ADJUST_PENALTY'


def user_transactions(sql_session: Session, user: User) -> list[Transaction]:
    """
    Returns the transactions of the user in chronological order.
    """

    return list(
        sql_session.scalars(
            select(Transaction)
            .where(Transaction.user_id == user.id)
            .order_by(Transaction.time.asc())
        ).all()
    )

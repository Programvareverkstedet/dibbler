from sqlalchemy import select
from sqlalchemy.orm import Session

from dibbler.models import Transaction, User
from dibbler.models.TransactionType import TransactionType


def user_transactions(
    sql_session: Session,
    user: User,
    transaction_type_filter: list[TransactionType] | None = None,
    negate_filter: bool = False,
) -> list[Transaction]:
    """
    Returns the transactions of the user in chronological order.
    """

    if transaction_type_filter is not None:
        if negate_filter:
            return list(
                sql_session.scalars(
                    select(Transaction)
                    .where(
                        Transaction.user_id == user.id,
                        Transaction.type_.not_in(transaction_type_filter),
                    )
                    .order_by(Transaction.time.asc())
                ).all()
            )
        else:
            return list(
                sql_session.scalars(
                    select(Transaction)
                    .where(
                        Transaction.user_id == user.id,
                        Transaction.type_.in_(transaction_type_filter),
                    )
                    .order_by(Transaction.time.asc())
                ).all()
            )

    return list(
        sql_session.scalars(
            select(Transaction)
            .where(Transaction.user_id == user.id)
            .order_by(Transaction.time.asc())
        ).all()
    )

from sqlalchemy import select
from sqlalchemy.orm import Session

from dibbler.models import Transaction, TransactionType
from dibbler.models.Transaction import DEFAULT_INTEREST_RATE_PERCENTAGE


def current_interest(sql_session: Session) -> int:
    result = sql_session.scalars(
        select(Transaction)
        .where(Transaction.type_ == TransactionType.ADJUST_INTEREST)
        .order_by(Transaction.time.desc())
        .limit(1)
    ).one_or_none()

    if result is None:
        return DEFAULT_INTEREST_RATE_PERCENTAGE

    assert result.interest_rate_percent is not None, "Interest rate percent must be set"

    return result.interest_rate_percent

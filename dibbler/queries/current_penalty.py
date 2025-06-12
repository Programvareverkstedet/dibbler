from sqlalchemy import select
from sqlalchemy.orm import Session

from dibbler.models import Transaction, TransactionType
from dibbler.models.Transaction import (
    DEFAULT_PENALTY_MULTIPLIER_PERCENTAGE,
    DEFAULT_PENALTY_THRESHOLD,
)


def current_penalty(sql_session: Session) -> tuple[int, int]:
    result = sql_session.scalars(
        select(Transaction)
        .where(Transaction.type_ == TransactionType.ADJUST_PENALTY)
        .order_by(Transaction.time.desc())
        .limit(1)
    ).one_or_none()

    if result is None:
        return DEFAULT_PENALTY_THRESHOLD, DEFAULT_PENALTY_MULTIPLIER_PERCENTAGE

    assert result.penalty_threshold is not None, "Penalty threshold must be set"
    assert result.penalty_multiplier_percent is not None, "Penalty multiplier percent must be set"

    return result.penalty_threshold, result.penalty_multiplier_percent

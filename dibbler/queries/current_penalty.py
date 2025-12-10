from datetime import datetime

from sqlalchemy import BindParameter, bindparam, select
from sqlalchemy.orm import Session

from dibbler.models import Transaction, TransactionType
from dibbler.models.Transaction import (
    DEFAULT_PENALTY_MULTIPLIER_PERCENT,
    DEFAULT_PENALTY_THRESHOLD,
)
from dibbler.queries.query_helpers import until_filter


def current_penalty(
    sql_session: Session,
    until_time: BindParameter[datetime] | datetime | None = None,
    until_transaction: BindParameter[Transaction] | Transaction | None = None,
    until_inclusive: bool = True,
) -> tuple[int, int]:
    """
    Get the current penalty settings (threshold and multiplier percentage) as of a given time or transaction.

    Returns a tuple of `(penalty_threshold, penalty_multiplier_percentage)`.
    """

    if not (until_time is None or until_transaction is None):
        raise ValueError("Cannot filter by both until_time and until_transaction.")

    if isinstance(until_time, datetime):
        until_time = BindParameter("until_time", value=until_time)

    if isinstance(until_transaction, Transaction):
        if until_transaction.id is None:
            raise ValueError("until_transaction must be persisted in the database.")
        until_transaction_id = bindparam("until_transaction_id", value=until_transaction.id)
    else:
        until_transaction_id = None

    result = sql_session.scalars(
        select(Transaction)
        .where(
            Transaction.type_ == TransactionType.ADJUST_PENALTY,
            until_filter(
                until_time=until_time,
                until_transaction_id=until_transaction_id,
                until_inclusive=until_inclusive,
            ),
        )
        .order_by(Transaction.time.desc())
        .limit(1),
    ).one_or_none()

    if result is None:
        return DEFAULT_PENALTY_THRESHOLD, DEFAULT_PENALTY_MULTIPLIER_PERCENT

    assert result.penalty_threshold is not None, "Penalty threshold must be set"
    assert result.penalty_multiplier_percent is not None, "Penalty multiplier percent must be set"

    return result.penalty_threshold, result.penalty_multiplier_percent

from datetime import datetime

from sqlalchemy.orm import Session

from dibbler.models import Transaction, User
from dibbler.models.Transaction import (
    DEFAULT_PENALTY_MULTIPLIER_PERCENTAGE,
    DEFAULT_PENALTY_THRESHOLD,
)
from dibbler.queries import current_penalty


def test_current_penalty_no_history(sql_session: Session) -> None:
    assert current_penalty(sql_session) == (
        DEFAULT_PENALTY_THRESHOLD,
        DEFAULT_PENALTY_MULTIPLIER_PERCENTAGE,
    )


def test_current_penalty_with_history(sql_session: Session) -> None:
    user = User("Admin User")
    sql_session.add(user)
    sql_session.commit()

    transactions = [
        Transaction.adjust_penalty(
            time=datetime(2023, 10, 1, 10, 0, 0),
            penalty_threshold=-200,
            penalty_multiplier_percent=150,
            user_id=user.id,
        ),
        Transaction.adjust_penalty(
            time=datetime(2023, 10, 2, 10, 0, 0),
            penalty_threshold=-300,
            penalty_multiplier_percent=200,
            user_id=user.id,
        ),
    ]
    sql_session.add_all(transactions)
    sql_session.commit()

    assert current_penalty(sql_session) == (-300, 200)

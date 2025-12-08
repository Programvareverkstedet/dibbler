from datetime import datetime

from sqlalchemy.orm import Session

from dibbler.models.Transaction import DEFAULT_INTEREST_RATE_PERCENTAGE
from dibbler.models import Transaction, User
from dibbler.queries.current_interest import current_interest

def test_current_interest_no_history(sql_session: Session) -> None:
    assert current_interest(sql_session) == DEFAULT_INTEREST_RATE_PERCENTAGE

def test_current_interest_with_history(sql_session: Session) -> None:
    user = User("Admin User")
    sql_session.add(user)
    sql_session.commit()

    transactions = [
        Transaction.adjust_interest(
            time=datetime(2023, 10, 1, 10, 0, 0),
            interest_rate_percent=5,
            user_id=user.id,
        ),
        Transaction.adjust_interest(
            time=datetime(2023, 11, 1, 10, 0, 0),
            interest_rate_percent=7,
            user_id=user.id,
        ),
    ]

    sql_session.add_all(transactions)
    sql_session.commit()

    assert current_interest(sql_session) == 7

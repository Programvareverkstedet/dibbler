from datetime import datetime

import pytest
from sqlalchemy.orm import Session

from dibbler.models import Transaction, User
from dibbler.queries import adjust_interest, current_interest


def insert_test_data(sql_session: Session) -> User:
    user = User("Test User")
    sql_session.add(user)
    sql_session.commit()

    return user


def test_adjust_interest_no_history(sql_session: Session) -> None:
    user = insert_test_data(sql_session)

    adjust_interest(
        sql_session,
        user=user,
        new_interest=3,
        message="Setting initial interest rate",
    )
    sql_session.commit()

    current_interest_rate = current_interest(sql_session)

    assert current_interest_rate == 3


def test_adjust_interest_existing_history(sql_session: Session) -> None:
    user = insert_test_data(sql_session)

    transactions = [
        Transaction.adjust_interest(
            time=datetime(2023, 10, 1, 9, 0, 0),
            user_id=user.id,
            interest_rate_percent=5,
            message="Initial interest rate",
        ),
    ]
    sql_session.add_all(transactions)
    sql_session.commit()

    current_interest_rate = current_interest(sql_session)
    assert current_interest_rate == 5

    adjust_interest(
        sql_session,
        user=user,
        new_interest=2,
        message="Adjusting interest rate",
    )
    sql_session.commit()

    current_interest_rate = current_interest(sql_session)
    assert current_interest_rate == 2


def test_adjust_interest_negative_failure(sql_session: Session) -> None:
    user = insert_test_data(sql_session)

    with pytest.raises(ValueError, match="Interest rate cannot be negative"):
        adjust_interest(
            sql_session,
            user=user,
            new_interest=-1,
            message="Attempting to set negative interest rate",
        )

from datetime import datetime

import pytest
from sqlalchemy.orm import Session

from dibbler.models import Transaction, User
from dibbler.models.Transaction import (
    DEFAULT_PENALTY_MULTIPLIER_PERCENTAGE,
    DEFAULT_PENALTY_THRESHOLD,
)
from dibbler.queries import adjust_penalty, current_penalty


def test_adjust_penalty_no_history(sql_session: Session) -> None:
    user = User("Test User")
    sql_session.add(user)
    sql_session.commit()

    adjust_penalty(
        sql_session,
        user_id=user.id,
        new_penalty=-200,
        message="Setting initial interest rate",
    )
    sql_session.commit()

    (penalty, multiplier) = current_penalty(sql_session)

    assert penalty == -200
    assert multiplier == DEFAULT_PENALTY_MULTIPLIER_PERCENTAGE


def test_adjust_penalty_multiplier_no_history(sql_session: Session) -> None:
    user = User("Test User")
    sql_session.add(user)
    sql_session.commit()

    adjust_penalty(
        sql_session,
        user_id=user.id,
        new_penalty_multiplier=125,
        message="Setting initial interest rate",
    )
    sql_session.commit()

    (penalty, multiplier) = current_penalty(sql_session)

    assert penalty == DEFAULT_PENALTY_THRESHOLD
    assert multiplier == 125


def test_adjust_penalty_multiplier_less_than_100_fail(sql_session: Session) -> None:
    user = User("Test User")
    sql_session.add(user)
    sql_session.commit()

    adjust_penalty(
        sql_session,
        user_id=user.id,
        new_penalty_multiplier=100,
        message="Setting initial interest rate",
    )
    sql_session.commit()

    (_, multiplier) = current_penalty(sql_session)

    assert multiplier == 100

    with pytest.raises(ValueError, match="Penalty multiplier cannot be less than 100%"):
        adjust_penalty(
            sql_session,
            user_id=user.id,
            new_penalty_multiplier=99,
            message="Setting initial interest rate",
        )


def test_adjust_penalty_existing_history(sql_session: Session) -> None:
    user = User("Test User")
    sql_session.add(user)
    sql_session.commit()

    transactions = [
        Transaction.adjust_penalty(
            time=datetime(2024, 1, 1, 10, 0, 0),
            user_id=user.id,
            penalty_threshold=-150,
            penalty_multiplier_percent=110,
            message="Initial penalty settings",
        ),
    ]
    sql_session.add_all(transactions)
    sql_session.commit()

    (penalty, _) = current_penalty(sql_session)
    assert penalty == -150

    adjust_penalty(
        sql_session,
        user_id=user.id,
        new_penalty=-250,
        message="Adjusting penalty threshold",
    )
    sql_session.commit()

    (penalty, _) = current_penalty(sql_session)
    assert penalty == -250


def test_adjust_penalty_multiplier_existing_history(sql_session: Session) -> None:
    user = User("Test User")
    sql_session.add(user)
    sql_session.commit()

    transactions = [
        Transaction.adjust_penalty(
            time=datetime(2024, 1, 1, 10, 0, 0),
            user_id=user.id,
            penalty_threshold=-150,
            penalty_multiplier_percent=110,
            message="Initial penalty settings",
        ),
    ]
    sql_session.add_all(transactions)
    sql_session.commit()

    (_, multiplier) = current_penalty(sql_session)
    assert multiplier == 110

    adjust_penalty(
        sql_session,
        user_id=user.id,
        new_penalty_multiplier=130,
        message="Adjusting penalty multiplier",
    )
    sql_session.commit()
    (_, multiplier) = current_penalty(sql_session)
    assert multiplier == 130


def test_adjust_penalty_and_multiplier(sql_session: Session) -> None:
    user = User("Test User")
    sql_session.add(user)
    sql_session.commit()

    adjust_penalty(
        sql_session,
        user_id=user.id,
        new_penalty=-300,
        new_penalty_multiplier=150,
        message="Setting both penalty and multiplier",
    )
    sql_session.commit()

    (penalty, multiplier) = current_penalty(sql_session)
    assert penalty == -300
    assert multiplier == 150

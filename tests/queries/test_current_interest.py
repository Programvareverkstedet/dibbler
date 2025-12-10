from sqlalchemy.orm import Session

from dibbler.models import Transaction, User
from dibbler.models.Transaction import DEFAULT_INTEREST_RATE_PERCENT
from dibbler.queries import current_interest
from tests.helpers import assert_id_order_similar_to_time_order, assign_times


def test_current_interest_no_history(sql_session: Session) -> None:
    assert current_interest(sql_session) == DEFAULT_INTEREST_RATE_PERCENT


def test_current_interest_with_history(sql_session: Session) -> None:
    user = User("Admin User")
    sql_session.add(user)
    sql_session.commit()

    transactions = [
        Transaction.adjust_interest(
            interest_rate_percent=5,
            user_id=user.id,
        ),
        Transaction.adjust_interest(
            interest_rate_percent=7,
            user_id=user.id,
        ),
    ]

    assign_times(transactions)

    sql_session.add_all(transactions)
    sql_session.commit()

    assert_id_order_similar_to_time_order(transactions)

    assert current_interest(sql_session) == 7

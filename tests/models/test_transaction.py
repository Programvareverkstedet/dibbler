from datetime import datetime

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from dibbler.models import Product, Transaction, User


def insert_test_data(sql_session: Session) -> tuple[User, Product]:
    user = User("Test User")
    product = Product("1234567890123", "Test Product")

    sql_session.add(user)
    sql_session.add(product)
    sql_session.commit()

    return user, product


def test_transaction_no_duplicate_timestamps(sql_session: Session):
    user, _ = insert_test_data(sql_session)

    transaction1 = Transaction.adjust_balance(
        time=datetime(2023, 10, 1, 12, 0, 0),
        user_id=user.id,
        amount=100,
    )

    sql_session.add(transaction1)
    sql_session.commit()

    transaction2 = Transaction.adjust_balance(
        time=transaction1.time,
        user_id=user.id,
        amount=-50,
    )

    sql_session.add(transaction2)

    with pytest.raises(IntegrityError):
        sql_session.commit()

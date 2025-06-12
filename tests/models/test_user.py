from datetime import datetime

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from dibbler.models import Product, Transaction, User


def insert_test_data(sql_session: Session) -> User:
    user = User("Test User")
    sql_session.add(user)
    sql_session.commit()

    return user


def test_ensure_no_duplicate_user_names(sql_session: Session):
    user = insert_test_data(sql_session)

    user2 = User(user.name)
    sql_session.add(user2)

    with pytest.raises(IntegrityError):
        sql_session.commit()


def test_user_transactions(sql_session: Session):
    user = insert_test_data(sql_session)

    product = Product("1234567890123", "Test Product")
    user2 = User("Test User 2")
    sql_session.add_all([product, user2])
    sql_session.commit()

    transactions = [
        Transaction.adjust_balance(
            time=datetime(2023, 10, 1, 10, 0, 0),
            amount=100,
            user_id=user.id,
        ),
        Transaction.adjust_balance(
            time=datetime(2023, 10, 1, 10, 0, 1),
            amount=50,
            user_id=user2.id,
        ),
        Transaction.adjust_balance(
            time=datetime(2023, 10, 1, 10, 0, 2),
            amount=-50,
            user_id=user.id,
        ),
        Transaction.add_product(
            time=datetime(2023, 10, 1, 12, 0, 0),
            amount=27 * 2,
            per_product=27,
            product_count=2,
            user_id=user.id,
            product_id=product.id,
        ),
        Transaction.buy_product(
            time=datetime(2023, 10, 1, 12, 0, 1),
            product_count=1,
            user_id=user2.id,
            product_id=product.id,
        ),
    ]

    sql_session.add_all(transactions)

    assert len(user.transactions(sql_session)) == 3
    assert len(user2.transactions(sql_session)) == 2

from datetime import datetime

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from dibbler.models import Product, Transaction, TransactionType, User


def insert_test_data(sql_session: Session) -> None:
    # Add users
    user1 = User("Test User 1")
    user2 = User("Test User 2")

    sql_session.add(user1)
    sql_session.add(user2)
    sql_session.commit()

    # Add products
    product1 = Product("1234567890123", "Test Product 1")
    product2 = Product("9876543210987", "Test Product 2")
    sql_session.add(product1)
    sql_session.add(product2)
    sql_session.commit()

    # Add transactions
    transactions = [
        Transaction(
            time=datetime(2023, 10, 1, 10, 0, 0),
            type_=TransactionType.ADJUST_BALANCE,
            amount=100,
            user_id=user1.id,
        ),
        Transaction(
            time=datetime(2023, 10, 1, 10, 0, 1),
            type_=TransactionType.ADJUST_BALANCE,
            amount=50,
            user_id=user2.id,
        ),
        Transaction(
            time=datetime(2023, 10, 1, 10, 0, 2),
            type_=TransactionType.ADJUST_BALANCE,
            amount=-50,
            user_id=user1.id,
        ),
        Transaction(
            time=datetime(2023, 10, 1, 12, 0, 0),
            type_=TransactionType.ADD_PRODUCT,
            amount=27 * 2,
            per_product=27,
            product_count=2,
            user_id=user1.id,
            product_id=product1.id,
        ),
        Transaction(
            time=datetime(2023, 10, 1, 12, 0, 1),
            type_=TransactionType.BUY_PRODUCT,
            amount=27,
            product_count=1,
            user_id=user2.id,
            product_id=product1.id,
        ),
    ]

    sql_session.add_all(transactions)
    sql_session.commit()


def test_ensure_no_duplicate_users(sql_session: Session):
    insert_test_data(sql_session)

    user1 = User("Test User 1")
    sql_session.add(user1)

    with pytest.raises(IntegrityError):
        sql_session.commit()


def test_user_credit(sql_session: Session):
    insert_test_data(sql_session)

    user1 = sql_session.scalars(select(User).where(User.name == "Test User 1")).one()
    user2 = sql_session.scalars(select(User).where(User.name == "Test User 2")).one()

    assert user1.credit(sql_session) == 100 - 50 + 27 * 2
    assert user2.credit(sql_session) == 50 - 27

def test_user_transactions(sql_session: Session):
    insert_test_data(sql_session)

    user1 = sql_session.scalars(select(User).where(User.name == "Test User 1")).one()
    user2 = sql_session.scalars(select(User).where(User.name == "Test User 2")).one()

    user1_transactions = user1.transactions(sql_session)
    user2_transactions = user2.transactions(sql_session)

    assert len(user1_transactions) == 3
    assert len(user2_transactions) == 2

def test_user_not_allowed_to_transfer_to_self(sql_session: Session):
    insert_test_data(sql_session)
    ...

    # user1 = sql_session.scalars(select(User).where(User.name == "Test User 1")).one()

    # with pytest.raises(ValueError, match="Cannot transfer to self"):
    #     user1.transfer(sql_session, user1, 10)  # Attempting to transfer to self

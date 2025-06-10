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

def test_no_duplicate_timestamps(sql_session: Session):
    """
    Ensure that no two transactions have the same timestamp.
    """
    # Insert test data
    insert_test_data(sql_session)

    user1 = sql_session.scalar(
        select(User).where(User.name == "Test User 1")
    )

    assert user1 is not None, "Test User 1 should exist"

    transaction_to_duplicate = sql_session.scalar(
        select(Transaction).limit(1)
    )

    assert transaction_to_duplicate is not None, "There should be at least one transaction"

    duplicate_timestamp_transaction = Transaction.adjust_balance(
        time=transaction_to_duplicate.time,  # Use the same timestamp as an existing transaction
        amount=50,
        user_id=user1.id,
    )

    with pytest.raises(IntegrityError):
        sql_session.add(duplicate_timestamp_transaction)
        sql_session.commit()

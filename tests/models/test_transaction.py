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


def test_user_not_allowed_to_transfer_to_self(sql_session: Session) -> None:
    user, _ = insert_test_data(sql_session)

    transaction = Transaction.transfer(
        time=datetime(2023, 10, 1, 12, 0, 0),
        user_id=user.id,
        transfer_user_id=user.id,
        amount=50,
    )

    sql_session.add(transaction)

    with pytest.raises(IntegrityError):
        sql_session.commit()


def test_product_foreign_key_constraint(sql_session: Session) -> None:
    user, product = insert_test_data(sql_session)

    transaction = Transaction.add_product(
        time=datetime(2023, 10, 1, 12, 0, 0),
        user_id=user.id,
        product_id=product.id,
        amount=27,
        per_product=27,
        product_count=1,
    )

    sql_session.add(transaction)
    sql_session.commit()

    # Attempt to add a transaction with a non-existent product
    invalid_transaction = Transaction.add_product(
        time=datetime(2023, 10, 1, 12, 0, 1),
        user_id=user.id,
        product_id=9999,  # Non-existent product ID
        amount=27,
        per_product=27,
        product_count=1,
    )

    sql_session.add(invalid_transaction)

    with pytest.raises(IntegrityError):
        sql_session.commit()


def test_user_foreign_key_constraint(sql_session: Session) -> None:
    user, product = insert_test_data(sql_session)

    transaction = Transaction.add_product(
        time=datetime(2023, 10, 1, 12, 0, 0),
        user_id=user.id,
        product_id=product.id,
        amount=27,
        per_product=27,
        product_count=1,
    )

    sql_session.add(transaction)
    sql_session.commit()

    # Attempt to add a transaction with a non-existent user
    invalid_transaction = Transaction.add_product(
        time=datetime(2023, 10, 1, 12, 0, 1),
        user_id=9999,  # Non-existent user ID
        product_id=product.id,
        amount=27,
        per_product=27,
        product_count=1,
    )

    sql_session.add(invalid_transaction)

    with pytest.raises(IntegrityError):
        sql_session.commit()

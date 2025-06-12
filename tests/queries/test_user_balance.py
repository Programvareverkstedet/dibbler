from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from dibbler.models import Product, Transaction, User
from dibbler.queries.user_balance import user_balance, user_balance_log


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
        Transaction.adjust_balance(
            time=datetime(2023, 10, 1, 10, 0, 0),
            amount=100,
            user_id=user1.id,
        ),
        Transaction.adjust_balance(
            time=datetime(2023, 10, 1, 10, 0, 1),
            amount=50,
            user_id=user2.id,
        ),
        Transaction.adjust_balance(
            time=datetime(2023, 10, 1, 10, 0, 2),
            amount=-50,
            user_id=user1.id,
        ),
        Transaction.add_product(
            time=datetime(2023, 10, 1, 12, 0, 0),
            amount=27 * 2,
            per_product=27,
            product_count=2,
            user_id=user1.id,
            product_id=product1.id,
        ),
        Transaction.buy_product(
            time=datetime(2023, 10, 1, 12, 0, 1),
            product_count=1,
            user_id=user2.id,
            product_id=product1.id,
        ),
    ]

    sql_session.add_all(transactions)
    sql_session.commit()


def test_user_balance_basic_history(sql_session: Session) -> None:
    insert_test_data(sql_session)

    user1 = sql_session.scalars(select(User).where(User.name == "Test User 1")).one()
    user2 = sql_session.scalars(select(User).where(User.name == "Test User 2")).one()

    assert user_balance(sql_session, user1) == 100 - 50 + 27 * 2
    assert user_balance(sql_session, user2) == 50 - 27


def test_user_balance_no_transactions(sql_session: Session) -> None:
    raise NotImplementedError("This test is not implemented yet.")


def test_user_balance_complex_history(sql_session: Session) -> None:
    raise NotImplementedError("This test is not implemented yet.")


def test_user_balance_with_tranfers(sql_session: Session) -> None:
    raise NotImplementedError("This test is not implemented yet.")


def test_user_balance_penalty(sql_session: Session) -> None:
    raise NotImplementedError("This test is not implemented yet.")


def test_user_balance_changing_penalty(sql_session: Session) -> None:
    raise NotImplementedError("This test is not implemented yet.")


def test_user_balance_interest(sql_session: Session) -> None:
    raise NotImplementedError("This test is not implemented yet.")


def test_user_balance_changing_interest(sql_session: Session) -> None:
    raise NotImplementedError("This test is not implemented yet.")


def test_user_balance_penalty_interest_combined(sql_session: Session) -> None:
    raise NotImplementedError("This test is not implemented yet.")

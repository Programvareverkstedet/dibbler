from datetime import datetime

from sqlalchemy.orm import Session

from dibbler.models import Product, Transaction, User
from dibbler.models.TransactionType import TransactionType
from dibbler.queries.user_transactions import user_transactions


def insert_test_data(sql_session: Session) -> User:
    user = User("Test User")
    sql_session.add(user)
    sql_session.commit()

    return user


def test_user_transactions_no_transactions(sql_session: Session):
    pass


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

    assert len(user_transactions(sql_session, user)) == 3
    assert len(user_transactions(sql_session, user2)) == 2


def test_filtered_user_transactions(sql_session: Session):
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

    assert (
        len(
            user_transactions(
                sql_session,
                user,
                transaction_type_filter=[TransactionType.ADJUST_BALANCE],
            )
        )
        == 2
    )
    assert (
        len(
            user_transactions(
                sql_session,
                user,
                transaction_type_filter=[TransactionType.ADJUST_BALANCE],
                negate_filter=True,
            )
        )
        == 1
    )
    assert (
        len(
            user_transactions(
                sql_session,
                user2,
                transaction_type_filter=[TransactionType.ADJUST_BALANCE],
            )
        )
        == 1
    )
    assert (
        len(
            user_transactions(
                sql_session,
                user2,
                transaction_type_filter=[TransactionType.ADJUST_BALANCE],
                negate_filter=True,
            )
        )
        == 1
    )


def test_user_transactions_joint_transactions(sql_session: Session):
    pass

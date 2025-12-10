from datetime import datetime

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from dibbler.models import Product, Transaction, User
from dibbler.models.TransactionType import TransactionTypeSQL
from dibbler.queries import joint_buy_product, product_stock


def insert_test_data(sql_session: Session) -> tuple[User, Product]:
    user = User("Test User 1")
    product = Product("1234567890123", "Test Product")
    sql_session.add(user)
    sql_session.add(product)
    sql_session.commit()
    return user, product


def test_product_stock_basic_history(sql_session: Session) -> None:
    user, product = insert_test_data(sql_session)

    sql_session.commit()

    transactions = [
        Transaction.add_product(
            time=datetime(2023, 10, 1, 12, 0, 0),
            amount=10,
            per_product=10,
            user_id=user.id,
            product_id=product.id,
            product_count=1,
        ),
    ]

    sql_session.add_all(transactions)
    sql_session.commit()

    assert product_stock(sql_session, product) == 1


def test_product_stock_adjust_stock_up(sql_session: Session) -> None:
    user, product = insert_test_data(sql_session)

    transactions = [
        Transaction.add_product(
            user_id=user.id,
            product_id=product.id,
            amount=50,
            per_product=10,
            product_count=5,
            time=datetime(2024, 1, 1, 10, 0, 0),
        ),
        Transaction.adjust_stock(
            user_id=user.id,
            product_id=product.id,
            product_count=2,
            time=datetime(2024, 1, 2, 10, 0, 0),
        ),
    ]
    sql_session.add_all(transactions)
    sql_session.commit()

    assert product_stock(sql_session, product) == 5 + 2


def test_product_stock_adjust_stock_down(sql_session: Session) -> None:
    user, product = insert_test_data(sql_session)

    transactions = [
        Transaction.add_product(
            user_id=user.id,
            product_id=product.id,
            amount=50,
            per_product=10,
            product_count=5,
            time=datetime(2024, 1, 1, 10, 0, 0),
        ),
        Transaction.adjust_stock(
            user_id=user.id,
            product_id=product.id,
            product_count=-2,
            time=datetime(2024, 1, 2, 10, 0, 0),
        ),
    ]
    sql_session.add_all(transactions)
    sql_session.commit()

    assert product_stock(sql_session, product) == 5 - 2


def test_product_stock_complex_history(sql_session: Session) -> None:
    user, product = insert_test_data(sql_session)

    transactions = [
        Transaction.add_product(
            time=datetime(2023, 10, 1, 13, 0, 0),
            amount=27 * 2,
            per_product=27,
            user_id=user.id,
            product_id=product.id,
            product_count=2,
        ),
        Transaction.buy_product(
            time=datetime(2023, 10, 1, 13, 0, 1),
            user_id=user.id,
            product_id=product.id,
            product_count=3,
        ),
        Transaction.add_product(
            time=datetime(2023, 10, 1, 13, 0, 2),
            amount=50 * 4,
            per_product=50,
            user_id=user.id,
            product_id=product.id,
            product_count=4,
        ),
        Transaction.adjust_stock(
            time=datetime(2023, 10, 1, 15, 0, 0),
            user_id=user.id,
            product_id=product.id,
            product_count=3,
        ),
        Transaction.adjust_stock(
            time=datetime(2023, 10, 1, 15, 0, 1),
            user_id=user.id,
            product_id=product.id,
            product_count=-2,
        ),
        Transaction.throw_product(
            time=datetime(2023, 10, 1, 15, 0, 2),
            user_id=user.id,
            product_id=product.id,
            product_count=1,
        ),
    ]

    sql_session.add_all(transactions)
    sql_session.commit()

    assert product_stock(sql_session, product) == 2 - 3 + 4 + 3 - 2 - 1


def test_product_stock_no_transactions(sql_session: Session) -> None:
    _, product = insert_test_data(sql_session)

    assert product_stock(sql_session, product) == 0


def test_negative_product_stock(sql_session: Session) -> None:
    user, product = insert_test_data(sql_session)

    transactions = [
        Transaction.add_product(
            time=datetime(2023, 10, 1, 14, 0, 0),
            amount=50,
            per_product=50,
            user_id=user.id,
            product_id=product.id,
            product_count=1,
        ),
        Transaction.buy_product(
            time=datetime(2023, 10, 1, 14, 0, 1),
            user_id=user.id,
            product_id=product.id,
            product_count=2,
        ),
        Transaction.adjust_stock(
            time=datetime(2023, 10, 1, 16, 0, 0),
            user_id=user.id,
            product_id=product.id,
            product_count=-1,
        ),
    ]

    sql_session.add_all(transactions)
    sql_session.commit()

    # The stock should be negative because we added and bought the product
    assert product_stock(sql_session, product) == 1 - 2 - 1


def test_product_stock_joint_transaction(sql_session: Session) -> None:
    user1, product = insert_test_data(sql_session)

    user2 = User("Test User 2")
    sql_session.add(user2)
    sql_session.commit()

    transactions = [
        Transaction.add_product(
            time=datetime(2023, 10, 1, 17, 0, 0),
            amount=100,
            per_product=100,
            user_id=user1.id,
            product_id=product.id,
            product_count=5,
        ),
    ]

    sql_session.add_all(transactions)
    sql_session.commit()

    joint_buy_product(
        sql_session,
        time=datetime(2023, 10, 1, 17, 0, 1),
        instigator=user1,
        users=[user1, user2],
        product=product,
        product_count=3,
    )

    assert product_stock(sql_session, product) == 5 - 3


def test_product_stock_until(sql_session: Session) -> None:
    user, product = insert_test_data(sql_session)

    transactions = [
        Transaction.add_product(
            time=datetime(2023, 10, 1, 12, 0, 0),
            amount=10,
            per_product=10,
            user_id=user.id,
            product_id=product.id,
            product_count=1,
        ),
        Transaction.add_product(
            time=datetime(2023, 10, 2, 12, 0, 0),
            amount=20,
            per_product=10,
            user_id=user.id,
            product_id=product.id,
            product_count=2,
        ),
    ]
    sql_session.add_all(transactions)
    sql_session.commit()

    assert product_stock(sql_session, product, until=datetime(2023, 10, 1, 23, 59, 59)) == 1

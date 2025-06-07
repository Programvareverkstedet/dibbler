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
            type=TransactionType.ADJUST_BALANCE,
            amount=100,
            user_id=user1.id,
        ),
        Transaction(
            time=datetime(2023, 10, 1, 10, 0, 0),
            type=TransactionType.ADJUST_BALANCE,
            amount=50,
            user_id=user2.id,
        ),
        Transaction(
            time=datetime(2023, 10, 1, 10, 0, 1),
            type=TransactionType.ADJUST_BALANCE,
            amount=-50,
            user_id=user1.id,
        ),
        Transaction(
            time=datetime(2023, 10, 1, 12, 0, 0),
            type=TransactionType.ADD_PRODUCT,
            amount=27 * 2,
            per_product=27,
            product_count=2,
            user_id=user1.id,
            product_id=product1.id,
        ),
        Transaction(
            time=datetime(2023, 10, 1, 12, 0, 1),
            type=TransactionType.BUY_PRODUCT,
            amount=27,
            product_count=1,
            user_id=user2.id,
            product_id=product1.id,
        ),
    ]

    sql_session.add_all(transactions)
    sql_session.commit()


def test_no_duplicate_products(sql_session: Session):
    insert_test_data(sql_session)

    product1 = Product("1234567890123", "Test Product 1")
    sql_session.add(product1)

    with pytest.raises(IntegrityError):
        sql_session.commit()


def test_product_stock(sql_session: Session):
    insert_test_data(sql_session)

    product1 = sql_session.scalars(select(Product).where(Product.name == "Test Product 1")).one()
    product2 = sql_session.scalars(select(Product).where(Product.name == "Test Product 2")).one()

    assert product1.stock(sql_session) == 1
    assert product2.stock(sql_session) == 0

def test_product_price(sql_session: Session):
    insert_test_data(sql_session)

    product1 = sql_session.scalars(select(Product).where(Product.name == "Test Product 1")).one()
    product2 = sql_session.scalars(select(Product).where(Product.name == "Test Product 2")).one()

    assert product1.price(sql_session) == 27
    assert product2.price(sql_session) == 0

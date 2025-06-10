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

    sql_session.add_all([user1, user2])
    sql_session.commit()

    # Add products
    product1 = Product("1234567890123", "Test Product 1")
    product2 = Product("9876543210987", "Test Product 2")
    product3 = Product("1111111111111", "Test Product 3")
    sql_session.add_all([product1, product2, product3])
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
        Transaction(
            time=datetime(2023, 10, 1, 12, 0, 2),
            type_=TransactionType.ADD_PRODUCT,
            amount=50,
            per_product=50,
            product_count=1,
            user_id=user1.id,
            product_id=product3.id,
        ),
        Transaction(
            time=datetime(2023, 10, 1, 12, 0, 3),
            type_=TransactionType.BUY_PRODUCT,
            amount=50,
            product_count=1,
            user_id=user1.id,
            product_id=product3.id,
        ),
        Transaction(
            time=datetime(2023, 10, 1, 12, 0, 4),
            type_=TransactionType.ADJUST_BALANCE,
            amount=1000,
            user_id=user1.id,
        ),
    ]

    sql_session.add_all(transactions)
    sql_session.commit()

    # Note: These constructors depend on the content of the previous transactions,
    #       so they cannot be part of the initial transaction list.

    transaction = Transaction.adjust_stock_auto_amount(
        sql_session=sql_session,
        time=datetime(2023, 10, 1, 13, 0, 0),
        product_count=3,
        user_id=user1.id,
        product_id=product1.id,
    )

    sql_session.add(transaction)
    sql_session.commit()

    transaction = Transaction.adjust_stock_auto_amount(
        sql_session=sql_session,
        time=datetime(2023, 10, 1, 13, 0, 1),
        product_count=-2,
        user_id=user1.id,
        product_id=product1.id,
    )

    sql_session.add(transaction)
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

    assert product1.stock(sql_session) == 2 - 1 + 3 - 2
    assert product2.stock(sql_session) == 0

def test_product_price(sql_session: Session):
    insert_test_data(sql_session)

    product1 = sql_session.scalars(select(Product).where(Product.name == "Test Product 1")).one()
    assert product1.price(sql_session) == 27


def test_product_no_transactions_price(sql_session: Session):
    insert_test_data(sql_session)

    product2 = sql_session.scalars(select(Product).where(Product.name == "Test Product 2")).one()
    assert product2.price(sql_session) == 0


def test_product_sold_out_price(sql_session: Session):
    insert_test_data(sql_session)

    product3 = sql_session.scalars(select(Product).where(Product.name == "Test Product 3")).one()
    assert product3.price(sql_session) == 50

def test_allowed_to_buy_more_than_stock(sql_session: Session):
    insert_test_data(sql_session)

    product1 = sql_session.scalars(select(Product).where(Product.name == "Test Product 1")).one()
    user1 = sql_session.scalars(select(User).where(User.name == "Test User 1")).one()

    transaction = Transaction.buy_product(
        time=datetime(2023, 10, 1, 12, 0, 6),
        amount = 27 * 5,
        product_count=10,
        user_id=user1.id,
        product_id=product1.id,
    )

    sql_session.add(transaction)
    sql_session.commit()

    product1_stock = product1.stock(sql_session)
    assert product1_stock < 0  # Should be negative, as we bought more than available stock

    product1_price = product1.price(sql_session)
    assert product1_price == 27  # Price should remain the same, as it is based on previous transactions

    transaction = Transaction.add_product(
        time=datetime(2023, 10, 1, 12, 0, 8),
        amount=22,
        per_product=22,
        product_count=1,
        user_id=user1.id,
        product_id=product1.id,
    )

    sql_session.add(transaction)
    sql_session.commit()

    product1_price = product1.price(sql_session)
    assert product1_price == 22  # Price should now be updated to the new price of the added product


def test_not_allowed_to_buy_with_incorrect_amount(sql_session: Session):
    insert_test_data(sql_session)

    product1 = sql_session.scalars(select(Product).where(Product.name == "Test Product 1")).one()
    user1 = sql_session.scalars(select(User).where(User.name == "Test User 1")).one()

    product1_price = product1.price(sql_session)

    with pytest.raises(IntegrityError):
        transaction = Transaction.buy_product(
            time=datetime(2023, 10, 1, 12, 0, 7),
            amount= product1_price * 4 + 1,  # Incorrect amount
            product_count=4,
            user_id=user1.id,
            product_id=product1.id,
        )
        sql_session.add(transaction)
        sql_session.commit()


def test_not_allowed_to_buy_with_too_little_balance(sql_session: Session):
    ...

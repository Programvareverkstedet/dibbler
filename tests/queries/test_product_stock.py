from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from dibbler.models import Product, Transaction, User
from dibbler.queries.product_stock import product_stock


def insert_test_data(sql_session: Session) -> None:
    user1 = User("Test User 1")

    sql_session.add(user1)
    sql_session.commit()


def test_product_stock_basic_history(sql_session: Session) -> None:
    insert_test_data(sql_session)

    user1 = sql_session.scalars(select(User).where(User.name == "Test User 1")).one()

    product = Product("1234567890123", "Test Product")
    sql_session.add(product)
    sql_session.commit()

    transactions = [
        Transaction.add_product(
            time=datetime(2023, 10, 1, 12, 0, 0),
            amount=10,
            per_product=10,
            user_id=user1.id,
            product_id=product.id,
            product_count=1,
        ),
    ]

    sql_session.add_all(transactions)
    sql_session.commit()

    assert product_stock(sql_session, product) == 1


def test_product_stock_complex_history(sql_session: Session) -> None:
    insert_test_data(sql_session)

    user1 = sql_session.scalars(select(User).where(User.name == "Test User 1")).one()

    product = Product("1234567890123", "Test Product")
    sql_session.add(product)
    sql_session.commit()

    transactions = [
        Transaction.add_product(
            time=datetime(2023, 10, 1, 13, 0, 0),
            amount=27 * 2,
            per_product=27,
            user_id=user1.id,
            product_id=product.id,
            product_count=2,
        ),
        Transaction.buy_product(
            time=datetime(2023, 10, 1, 13, 0, 1),
            user_id=user1.id,
            product_id=product.id,
            product_count=3,
        ),
        Transaction.add_product(
            time=datetime(2023, 10, 1, 13, 0, 2),
            amount=50 * 4,
            per_product=50,
            user_id=user1.id,
            product_id=product.id,
            product_count=4,
        ),
        Transaction.adjust_stock(
            time=datetime(2023, 10, 1, 15, 0, 0),
            user_id=user1.id,
            product_id=product.id,
            product_count=3,
        ),
        Transaction.adjust_stock(
            time=datetime(2023, 10, 1, 15, 0, 1),
            user_id=user1.id,
            product_id=product.id,
            product_count=-2,
        ),
    ]

    sql_session.add_all(transactions)
    sql_session.commit()

    assert product_stock(sql_session, product) == 2 - 3 + 4 + 3 - 2


def test_product_stock_no_transactions(sql_session: Session) -> None:
    insert_test_data(sql_session)

    product = Product("1234567890123", "Test Product")
    sql_session.add(product)
    sql_session.commit()

    assert product_stock(sql_session, product) == 0


def test_negative_product_stock(sql_session: Session) -> None:
    insert_test_data(sql_session)

    user1 = sql_session.scalars(select(User).where(User.name == "Test User 1")).one()

    product = Product("1234567890123", "Test Product")
    sql_session.add(product)
    sql_session.commit()

    transactions = [
        Transaction.add_product(
            time=datetime(2023, 10, 1, 14, 0, 0),
            amount=50,
            per_product=50,
            user_id=user1.id,
            product_id=product.id,
            product_count=1,
        ),
        Transaction.buy_product(
            time=datetime(2023, 10, 1, 14, 0, 1),
            user_id=user1.id,
            product_id=product.id,
            product_count=2,
        ),
        Transaction.adjust_stock(
            time=datetime(2023, 10, 1, 16, 0, 0),
            user_id=user1.id,
            product_id=product.id,
            product_count=-1,
        ),
    ]

    sql_session.add_all(transactions)
    sql_session.commit()

    # The stock should be negative because we added and bought the product
    assert product_stock(sql_session, product) == 1 - 2 - 1

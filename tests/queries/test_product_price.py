from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from dibbler.models import Product, Transaction, User
from dibbler.queries.product_price import product_price


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
        Transaction.adjust_stock(
            time=datetime(2023, 10, 1, 12, 0, 2),
            product_count=3,
            user_id=user1.id,
            product_id=product1.id,
        ),
        Transaction.adjust_stock(
            time=datetime(2023, 10, 1, 12, 0, 3),
            product_count=-2,
            user_id=user1.id,
            product_id=product1.id,
        ),
        Transaction.add_product(
            time=datetime(2023, 10, 1, 12, 0, 4),
            amount=50,
            per_product=50,
            product_count=1,
            user_id=user1.id,
            product_id=product3.id,
        ),
        Transaction.buy_product(
            time=datetime(2023, 10, 1, 12, 0, 5),
            product_count=1,
            user_id=user1.id,
            product_id=product3.id,
        ),
        Transaction.adjust_balance(
            time=datetime(2023, 10, 1, 12, 0, 6),
            amount=1000,
            user_id=user1.id,
        ),
    ]

    sql_session.add_all(transactions)
    sql_session.commit()


def test_product_price(sql_session: Session) -> None:
    insert_test_data(sql_session)

    product1 = sql_session.scalars(select(Product).where(Product.name == "Test Product 1")).one()
    assert product_price(sql_session, product1) == 27


def test_product_price_no_transactions(sql_session: Session) -> None:
    insert_test_data(sql_session)

    product2 = sql_session.scalars(select(Product).where(Product.name == "Test Product 2")).one()
    assert product_price(sql_session, product2) == 0


def test_product_price_sold_out(sql_session: Session) -> None:
    insert_test_data(sql_session)

    product3 = sql_session.scalars(select(Product).where(Product.name == "Test Product 3")).one()
    assert product_price(sql_session, product3) == 50


def test_product_price_interest(sql_session: Session) -> None:
    raise NotImplementedError("This test is not implemented yet.")


def test_product_price_changing_interest(sql_session: Session) -> None:
    raise NotImplementedError("This test is not implemented yet.")


# Price goes up and gets rounded up to the next integer
def test_product_price_round_up_from_below(sql_session: Session) -> None:
    raise NotImplementedError("This test is not implemented yet.")


# Price goes down and gets rounded up to the next integer
def test_product_price_round_up_from_above(sql_session: Session) -> None:
    raise NotImplementedError("This test is not implemented yet.")


def test_product_price_with_negative_stock_single_addition(sql_session: Session) -> None:
    insert_test_data(sql_session)

    product1 = sql_session.scalars(select(Product).where(Product.name == "Test Product 1")).one()
    user1 = sql_session.scalars(select(User).where(User.name == "Test User 1")).one()

    transaction = Transaction.buy_product(
        time=datetime(2023, 10, 1, 13, 0, 0),
        product_count=10,
        user_id=user1.id,
        product_id=product1.id,
    )

    sql_session.add(transaction)
    sql_session.commit()

    product1_price = product_price(sql_session, product1)
    assert product1_price == 27

    transaction = Transaction.add_product(
        time=datetime(2023, 10, 1, 13, 0, 1),
        amount=22,
        per_product=22,
        product_count=1,
        user_id=user1.id,
        product_id=product1.id,
    )

    sql_session.add(transaction)
    sql_session.commit()

    # Stock went subzero, price should be the last added product price
    product1_price = product_price(sql_session, product1)
    assert product1_price == 22


# TODO: what happens when stock is still negative and yet new products are added?
def test_product_price_with_negative_stock_multiple_additions(sql_session: Session) -> None:
    raise NotImplementedError("This test is not implemented yet.")

import math
from datetime import datetime

from sqlalchemy.orm import Session

from dibbler.models import Product, Transaction, User
from dibbler.queries.buy_product import buy_product
from dibbler.queries.product_stock import product_stock
from dibbler.queries.user_balance import user_balance


def insert_test_data(sql_session: Session) -> tuple[User, Product]:
    user = User("Test User")
    product = Product("1234567890123", "Test Product")

    sql_session.add(user)
    sql_session.add(product)
    sql_session.commit()

    transactions = [
        Transaction.adjust_penalty(
            time=datetime(2023, 10, 1, 10, 0, 0),
            user_id=user.id,
            penalty_multiplier_percent=200,
            penalty_threshold=-100,
        ),
        Transaction.adjust_balance(
            time=datetime(2023, 10, 1, 10, 0, 1),
            user_id=user.id,
            amount=100,
        ),
        Transaction.add_product(
            time=datetime(2023, 10, 1, 10, 0, 2),
            user_id=user.id,
            product_id=product.id,
            amount=27,
            per_product=27,
            product_count=1,
        ),
    ]

    sql_session.add_all(transactions)
    sql_session.commit()

    return user, product


def test_buy_product_basic(sql_session: Session) -> None:
    user, product = insert_test_data(sql_session)

    transaction = buy_product(
        sql_session=sql_session,
        time=datetime(2023, 10, 1, 12, 0, 0),
        user=user,
        product=product,
        product_count=1,
    )

    sql_session.add(transaction)
    sql_session.commit()


def test_buy_product_with_penalty(sql_session: Session) -> None:
    user, product = insert_test_data(sql_session)

    transactions = [
        Transaction.adjust_balance(
            time=datetime(2023, 10, 1, 11, 0, 0),
            user_id=user.id,
            amount=-200,
        )
    ]
    sql_session.add_all(transactions)
    sql_session.commit()

    transaction = buy_product(
        sql_session=sql_session,
        time=datetime(2023, 10, 1, 12, 0, 0),
        user=user,
        product=product,
        product_count=1,
    )
    sql_session.add(transaction)
    sql_session.commit()

    assert user_balance(sql_session, user) == 100 + 27 - 200 - (27 * 2)


def test_buy_product_with_interest(sql_session: Session) -> None:
    user, product = insert_test_data(sql_session)

    transactions = [
        Transaction.adjust_interest(
            time=datetime(2023, 10, 1, 11, 0, 0),
            user_id=user.id,
            interest_rate_percent=110,
        )
    ]
    sql_session.add_all(transactions)
    sql_session.commit()

    transaction = buy_product(
        sql_session=sql_session,
        time=datetime(2023, 10, 1, 12, 0, 0),
        user=user,
        product=product,
        product_count=1,
    )
    sql_session.add(transaction)
    sql_session.commit()

    assert user_balance(sql_session, user) == 100 + 27 - math.ceil(27 * 1.1)


def test_buy_product_with_changing_penalty(sql_session: Session) -> None:
    user, product = insert_test_data(sql_session)

    transactions = [
        Transaction.adjust_balance(
            time=datetime(2023, 10, 1, 11, 0, 0),
            user_id=user.id,
            amount=-200,
        )
    ]
    sql_session.add_all(transactions)
    sql_session.commit()

    transaction = buy_product(
        sql_session=sql_session,
        time=datetime(2023, 10, 1, 12, 0, 0),
        user=user,
        product=product,
        product_count=1,
    )
    sql_session.add(transaction)
    sql_session.commit()

    assert user_balance(sql_session, user) == 100 + 27 - 200 - (27 * 2)

    adjust_penalty = Transaction.adjust_penalty(
        time=datetime(2023, 10, 1, 13, 0, 0),
        user_id=user.id,
        penalty_multiplier_percent=300,
        penalty_threshold=-100,
    )
    sql_session.add(adjust_penalty)
    sql_session.commit()

    transaction = buy_product(
        sql_session=sql_session,
        time=datetime(2023, 10, 1, 14, 0, 0),
        user=user,
        product=product,
        product_count=1,
    )
    sql_session.add(transaction)
    sql_session.commit()

    assert user_balance(sql_session, user) == 100 + 27 - 200 - (27 * 2) - (27 * 3)


def test_buy_product_with_changing_interest(sql_session: Session) -> None:
    raise NotImplementedError("This test is not implemented yet.")


def test_buy_product_with_penalty_interest_combined(sql_session: Session) -> None:
    raise NotImplementedError("This test is not implemented yet.")


def test_buy_product_more_than_stock(sql_session: Session) -> None:
    user, product = insert_test_data(sql_session)

    transaction = buy_product(
        sql_session=sql_session,
        time=datetime(2023, 10, 1, 13, 0, 0),
        product_count=10,
        user=user,
        product=product,
    )

    sql_session.add(transaction)
    sql_session.commit()

    assert product_stock(sql_session, product) == 1 - 10

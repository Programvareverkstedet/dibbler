from datetime import datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from dibbler.models import Product, Transaction, User
from dibbler.queries import joint_buy_product, product_stock
from tests.helpers import assert_id_order_similar_to_time_order, assign_times


def insert_test_data(sql_session: Session) -> tuple[User, Product]:
    user = User("Test User 1")
    product = Product("1234567890123", "Test Product")
    sql_session.add(user)
    sql_session.add(product)
    sql_session.commit()
    return user, product


def test_product_stock_uninitialized_product(sql_session: Session) -> None:
    user = User("Test User 1")
    sql_session.add(user)
    sql_session.commit()

    product = Product("1234567890123", "Uninitialized Product")

    with pytest.raises(ValueError):
        product_stock(sql_session, product)


def test_product_stock_until_datetime_and_transaction_id_not_allowed(sql_session: Session) -> None:
    user, product = insert_test_data(sql_session)

    transaction = Transaction.add_product(
        amount=10,
        per_product=10,
        user_id=user.id,
        product_id=product.id,
        product_count=1,
    )

    with pytest.raises(ValueError):
        product_stock(
            sql_session,
            product,
            until_time=datetime.now(),
            until_transaction=transaction,
        )


def test_product_stock_basic_history(sql_session: Session) -> None:
    user, product = insert_test_data(sql_session)

    sql_session.commit()

    transactions = [
        Transaction.add_product(
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
        ),
        Transaction.adjust_stock(
            user_id=user.id,
            product_id=product.id,
            product_count=2,
        ),
    ]

    assign_times(transactions)

    sql_session.add_all(transactions)
    sql_session.commit()

    assert_id_order_similar_to_time_order(transactions)

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
        ),
        Transaction.adjust_stock(
            user_id=user.id,
            product_id=product.id,
            product_count=-2,
        ),
    ]

    assign_times(transactions)

    sql_session.add_all(transactions)
    sql_session.commit()

    assert_id_order_similar_to_time_order(transactions)

    assert product_stock(sql_session, product) == 5 - 2


def test_product_stock_complex_history(sql_session: Session) -> None:
    user, product = insert_test_data(sql_session)

    transactions = [
        Transaction.add_product(
            amount=27 * 2,
            per_product=27,
            user_id=user.id,
            product_id=product.id,
            product_count=2,
        ),
        Transaction.buy_product(
            user_id=user.id,
            product_id=product.id,
            product_count=3,
        ),
        Transaction.add_product(
            amount=50 * 4,
            per_product=50,
            user_id=user.id,
            product_id=product.id,
            product_count=4,
        ),
        Transaction.adjust_stock(
            user_id=user.id,
            product_id=product.id,
            product_count=3,
        ),
        Transaction.adjust_stock(
            user_id=user.id,
            product_id=product.id,
            product_count=-2,
        ),
        Transaction.throw_product(
            user_id=user.id,
            product_id=product.id,
            product_count=1,
        ),
    ]

    assign_times(transactions)

    sql_session.add_all(transactions)
    sql_session.commit()

    assert_id_order_similar_to_time_order(transactions)

    assert product_stock(sql_session, product) == 2 - 3 + 4 + 3 - 2 - 1


def test_product_stock_no_transactions(sql_session: Session) -> None:
    _, product = insert_test_data(sql_session)

    assert product_stock(sql_session, product) == 0


def test_negative_product_stock(sql_session: Session) -> None:
    user, product = insert_test_data(sql_session)

    transactions = [
        Transaction.add_product(
            amount=50,
            per_product=50,
            user_id=user.id,
            product_id=product.id,
            product_count=1,
        ),
        Transaction.buy_product(
            user_id=user.id,
            product_id=product.id,
            product_count=2,
        ),
        Transaction.adjust_stock(
            user_id=user.id,
            product_id=product.id,
            product_count=-1,
        ),
    ]

    assign_times(transactions)

    sql_session.add_all(transactions)
    sql_session.commit()

    assert_id_order_similar_to_time_order(transactions)

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
        time=transactions[0].time + timedelta(seconds=1),
        instigator=user1,
        users=[user1, user2],
        product=product,
        product_count=3,
    )

    assert product_stock(sql_session, product) == 5 - 3


def test_product_stock_until_time(sql_session: Session) -> None:
    user, product = insert_test_data(sql_session)

    transactions = [
        Transaction.add_product(
            amount=10,
            per_product=10,
            user_id=user.id,
            product_id=product.id,
            product_count=1,
        ),
        Transaction.add_product(
            amount=20,
            per_product=10,
            user_id=user.id,
            product_id=product.id,
            product_count=2,
        ),
    ]

    assign_times(transactions)

    sql_session.add_all(transactions)
    sql_session.commit()

    assert_id_order_similar_to_time_order(transactions)

    assert (
        product_stock(
            sql_session,
            product,
            until_time=transactions[-1].time - timedelta(seconds=1),
        )
        == 1
    )

from datetime import datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from dibbler.models import Product, Transaction, User
from dibbler.queries import affected_users
from tests.helpers import assert_id_order_similar_to_time_order, assign_times


def insert_test_data(sql_session: Session) -> tuple[list[User], Product]:
    users = []
    for i in range(10):
        user = User(f"Test User {i + 1}")
        users.append(user)

    product = Product("1234567890123", "Test Product")

    sql_session.add_all(users)
    sql_session.add(product)
    sql_session.commit()

    return users, product


def test_affected_users_no_history(sql_session: Session) -> None:
    insert_test_data(sql_session)

    result = affected_users(sql_session)

    assert result == set()


def test_affected_users_basic_history(sql_session: Session) -> None:
    users, product = insert_test_data(sql_session)

    transactions = [
        Transaction.add_product(
            amount=10,
            per_product=10,
            user_id=users[i].id,
            product_id=product.id,
            product_count=1,
        )
        for i in range(5)
    ] + [
        Transaction.buy_product(
            user_id=users[i].id,
            product_id=product.id,
            product_count=1,
        )
        for i in range(3)
    ]

    assign_times(transactions)

    sql_session.add_all(transactions)
    sql_session.commit()

    assert_id_order_similar_to_time_order(transactions)

    result = affected_users(sql_session)

    expected_users = {users[i] for i in range(5)}

    assert result == expected_users


# def test_affected_users_after(sql_session: Session) -> None:
# def test_affected_users_until(sql_session: Session) -> None:
# def test_affected_users_after_until(sql_session: Session) -> None:
# def test_affected_users_after_inclusive(sql_session: Session) -> None:
# def test_affected_users_until_inclusive(sql_session: Session) -> None:
# def test_affected_users_after_until_inclusive(sql_session: Session) -> None:

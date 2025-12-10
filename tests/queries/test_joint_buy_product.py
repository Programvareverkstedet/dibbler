from datetime import datetime

import pytest
from sqlalchemy.orm import Session

from dibbler.models import Product, Transaction, User
from dibbler.queries import joint_buy_product


def insert_test_data(sql_session: Session) -> tuple[User, User, User, Product]:
    user1 = User("Test User 1")
    user2 = User("Test User 2")
    user3 = User("Test User 3")
    product = Product("1234567890123", "Test Product")

    sql_session.add_all([user1, user2, user3, product])
    sql_session.commit()

    transactions = [
        Transaction.add_product(
            user_id=user1.id,
            product_id=product.id,
            amount=30,
            per_product=10,
            product_count=3,
            time=datetime(2024, 1, 1, 10, 0, 0),
        )
    ]

    sql_session.add_all(transactions)
    sql_session.commit()

    return user1, user2, user3, product


def test_joint_buy_product_missing_product(sql_session: Session) -> None:
    user = User("Test User 1")
    sql_session.add(user)
    sql_session.commit()

    product = Product("1234567890123", "Test Product")

    with pytest.raises(ValueError):
        joint_buy_product(
            sql_session,
            instigator=user,
            users=[user],
            product=product,
            product_count=1,
        )


def test_joint_buy_product_missing_user(sql_session: Session) -> None:
    user = User("Test User 1")

    product = Product("1234567890123", "Test Product")
    sql_session.add(product)
    sql_session.commit()

    with pytest.raises(ValueError):
        joint_buy_product(
            sql_session,
            instigator=user,
            users=[user],
            product=product,
            product_count=1,
        )


def test_joint_buy_product_invalid_product_count(sql_session: Session) -> None:
    user, _, _, product = insert_test_data(sql_session)

    with pytest.raises(ValueError):
        joint_buy_product(
            sql_session,
            instigator=user,
            users=[user],
            product=product,
            product_count=0,
        )

    with pytest.raises(ValueError):
        joint_buy_product(
            sql_session,
            instigator=user,
            users=[user],
            product=product,
            product_count=-1,
        )


def test_joint_single_user(sql_session: Session) -> None:
    user, _, _, product = insert_test_data(sql_session)

    joint_buy_product(
        sql_session,
        instigator=user,
        users=[user],
        product=product,
        product_count=1,
    )


def test_joint_buy_product(sql_session: Session) -> None:
    user, user2, user3, product = insert_test_data(sql_session)

    joint_buy_product(
        sql_session,
        instigator=user,
        users=[user, user2, user3],
        product=product,
        product_count=1,
    )


def test_joint_buy_product_more_than_in_stock(sql_session: Session) -> None:
    user, user2, user3, product = insert_test_data(sql_session)

    joint_buy_product(
        sql_session,
        instigator=user,
        users=[user, user2, user3],
        product=product,
        product_count=5,
    )


def test_joint_buy_product_out_of_stock(sql_session: Session) -> None:
    user, user2, user3, product = insert_test_data(sql_session)

    transactions = [
        Transaction.buy_product(
            user_id=user.id,
            product_id=product.id,
            product_count=3,
            time=datetime(2024, 1, 2, 10, 0, 0),
        )
    ]

    sql_session.add_all(transactions)
    sql_session.commit()

    joint_buy_product(
        sql_session,
        instigator=user,
        users=[user, user2, user3],
        product=product,
        product_count=10,
    )


def test_joint_buy_product_duplicate_user(sql_session: Session) -> None:
    user, user2, _, product = insert_test_data(sql_session)

    joint_buy_product(
        sql_session,
        instigator=user,
        users=[user, user, user2],
        product=product,
        product_count=1,
    )


def test_joint_buy_product_non_involved_instigator(sql_session: Session) -> None:
    user, user2, user3, product = insert_test_data(sql_session)

    with pytest.raises(ValueError):
        joint_buy_product(
            sql_session,
            instigator=user,
            users=[user2, user3],
            product=product,
            product_count=1,
        )

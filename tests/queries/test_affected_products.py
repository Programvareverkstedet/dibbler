from datetime import datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from dibbler.models import Product, Transaction, User
from dibbler.queries import affected_products
from tests.helpers import assert_id_order_similar_to_time_order, assign_times


def insert_test_data(sql_session: Session) -> tuple[User, list[Product]]:
    user = User("Test User")

    products = []
    for i in range(10):
        product = Product(f"12345678901{i:02d}", f"Test Product {i}")
        products.append(product)

    sql_session.add(user)
    sql_session.add_all(products)
    sql_session.commit()

    return user, products


def test_affected_products_no_history(sql_session: Session) -> None:
    insert_test_data(sql_session)

    result = affected_products(sql_session)

    assert result == set()


def test_affected_products_basic_history(sql_session: Session) -> None:
    user, products = insert_test_data(sql_session)

    transactions = [
        Transaction.add_product(
            amount=10,
            per_product=10,
            user_id=user.id,
            product_id=products[i].id,
            product_count=1,
        )
        for i in range(5)
    ] + [
        Transaction.buy_product(
            user_id=user.id,
            product_id=products[i].id,
            product_count=1,
        )
        for i in range(3)
    ]

    assign_times(transactions)

    sql_session.add_all(transactions)
    sql_session.commit()

    assert_id_order_similar_to_time_order(transactions)

    result = affected_products(sql_session)

    expected_products = {products[i] for i in range(5)}

    assert result == expected_products


# def test_affected_products_after(sql_session: Session) -> None:
# def test_affected_products_until(sql_session: Session) -> None:
# def test_affected_products_after_until(sql_session: Session) -> None:
# def test_affected_products_after_inclusive(sql_session: Session) -> None:
# def test_affected_products_until_inclusive(sql_session: Session) -> None:
# def test_affected_products_after_until_inclusive(sql_session: Session) -> None:

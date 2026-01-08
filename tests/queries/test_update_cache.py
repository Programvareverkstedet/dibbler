import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from dibbler.models import Product, ProductCache, Transaction, User, UserCache
from dibbler.models.LastCacheTransaction import LastCacheTransaction
from dibbler.queries import update_cache
from tests.helpers import assert_id_order_similar_to_time_order, assign_times


def insert_test_data(sql_session: Session) -> tuple[User, User, Product, Product]:
    user1 = User("Test User")
    user2 = User("Another User")
    product1 = Product("1234567890123", "Test Product 1")
    product2 = Product("9876543210987", "Test Product 2")

    sql_session.add_all([user1, user2, product1, product2])
    sql_session.commit()

    return user1, user2, product1, product2


def get_cache_entries(sql_session: Session) -> tuple[list[UserCache], list[ProductCache]]:
    user_cache = sql_session.scalars(
        select(UserCache)
        .join(LastCacheTransaction, UserCache.last_cache_transaction_id == LastCacheTransaction.id)
        .join(Transaction, LastCacheTransaction.transaction_id == Transaction.id)
        .order_by(Transaction.time.asc(), UserCache.user_id),
    ).all()

    product_cache = sql_session.scalars(
        select(ProductCache)
        .join(
            LastCacheTransaction, ProductCache.last_cache_transaction_id == LastCacheTransaction.id,
        )
        .join(Transaction, LastCacheTransaction.transaction_id == Transaction.id)
        .order_by(Transaction.time.asc(), ProductCache.product_id),
    ).all()

    return list(user_cache), list(product_cache)


def test_affected_update_cache_no_history(sql_session: Session) -> None:
    insert_test_data(sql_session)

    update_cache(sql_session)


def test_affected_update_cache_basic_history(sql_session: Session) -> None:
    user1, user2, product1, product2 = insert_test_data(sql_session)

    transactions = [
        Transaction.add_product(
            amount=10,
            per_product=10,
            user_id=user1.id,
            product_id=product1.id,
            product_count=1,
        ),
        Transaction.add_product(
            amount=20,
            per_product=10,
            user_id=user2.id,
            product_id=product2.id,
            product_count=2,
        ),
    ]

    assign_times(transactions)

    sql_session.add_all(transactions)
    sql_session.commit()

    assert_id_order_similar_to_time_order(transactions)

    update_cache(sql_session)

    user_cache = sql_session.scalars(select(UserCache).order_by(UserCache.user_id)).all()
    product_cache = sql_session.scalars(
        select(ProductCache).order_by(ProductCache.product_id),
    ).all()

    assert user_cache[0].user_id == user1.id
    assert user_cache[0].balance == 10
    assert user_cache[1].user_id == user2.id
    assert user_cache[1].balance == 20

    assert product_cache[0].product_id == product1.id
    assert product_cache[0].stock == 1
    assert product_cache[0].price == 10

    assert product_cache[1].product_id == product2.id
    assert product_cache[1].stock == 2
    assert product_cache[1].price == 10


def test_update_cache_multiple_times_no_changes(sql_session: Session) -> None:
    user1, user2, product1, product2 = insert_test_data(sql_session)

    transactions = [
        Transaction.add_product(
            amount=10,
            per_product=10,
            user_id=user1.id,
            product_id=product1.id,
            product_count=1,
        ),
        Transaction.add_product(
            amount=20,
            per_product=10,
            user_id=user2.id,
            product_id=product2.id,
            product_count=2,
        ),
    ]

    assign_times(transactions)

    sql_session.add_all(transactions)
    sql_session.commit()

    assert_id_order_similar_to_time_order(transactions)

    update_cache(sql_session)

    update_cache(sql_session)

    user_cache, product_cache = get_cache_entries(sql_session)

    assert user_cache[0].user_id == user1.id
    assert user_cache[0].balance == 10
    assert user_cache[1].user_id == user2.id
    assert user_cache[1].balance == 20


def test_update_cache_multiple_times(sql_session: Session) -> None:
    user1, user2, product1, product2 = insert_test_data(sql_session)

    transactions = [
        Transaction.add_product(
            amount=10,
            per_product=10,
            user_id=user1.id,
            product_id=product1.id,
            product_count=1,
        ),
        Transaction.add_product(
            amount=20,
            per_product=10,
            user_id=user2.id,
            product_id=product2.id,
            product_count=2,
        ),
    ]

    assign_times(transactions)

    sql_session.add_all(transactions)
    sql_session.commit()

    assert_id_order_similar_to_time_order(transactions)

    update_cache(sql_session)

    transactions_more = [
        Transaction.add_product(
            amount=30,
            per_product=10,
            user_id=user1.id,
            product_id=product1.id,
            product_count=3,
        ),
        Transaction.buy_product(
            user_id=user1.id,
            product_id=product1.id,
            product_count=1,
        ),
    ]

    assign_times(transactions_more, start_time=transactions[-1].time)

    sql_session.add_all(transactions_more)
    sql_session.commit()

    assert_id_order_similar_to_time_order(transactions_more)

    update_cache(sql_session)

    user_cache, product_cache = get_cache_entries(sql_session)

    assert user_cache[0].user_id == user1.id
    assert user_cache[0].balance == 10
    assert user_cache[1].user_id == user2.id
    assert user_cache[1].balance == 20
    assert product_cache[0].product_id == product1.id
    assert product_cache[0].stock == 1
    assert product_cache[0].price == 10
    assert product_cache[1].product_id == product2.id
    assert product_cache[1].stock == 2
    assert product_cache[1].price == 10

    assert user_cache[2].user_id == user1.id
    assert user_cache[2].balance == 10 + 30 - 10
    assert product_cache[2].product_id == product1.id
    assert product_cache[2].stock == 1 + 3 - 1
    assert product_cache[2].price == 10

import math
from datetime import datetime, timedelta
from pprint import pprint

import pytest
from sqlalchemy.orm import Session

from dibbler.models import Product, Transaction, User
from dibbler.queries import joint_buy_product, product_price, product_price_log
from tests.helpers import assert_id_order_similar_to_time_order, assign_times

# TODO: see if we can use pytest_runtest_makereport to print the "product_price_log"s
#       only on failures instead of inlining it in every test function


def insert_test_data(sql_session: Session) -> tuple[User, Product]:
    user = User("Test User")
    product = Product("1234567890123", "Test Product")

    sql_session.add(user)
    sql_session.add(product)
    sql_session.commit()

    return user, product


def test_product_price_uninitialized_product(sql_session: Session) -> None:
    user = User("Test User")
    sql_session.add(user)
    sql_session.commit()

    product = Product("1234567890123", "Uninitialized Product")

    with pytest.raises(ValueError, match="Product must be persisted in the database."):
        product_price(sql_session, product)


def test_product_price_no_transactions(sql_session: Session) -> None:
    _, product = insert_test_data(sql_session)

    pprint(product_price_log(sql_session, product))

    assert product_price(sql_session, product) == 0


def test_product_price_basic_history(sql_session: Session) -> None:
    user, product = insert_test_data(sql_session)

    transactions = [
        Transaction.add_product(
            time=datetime(2023, 10, 1, 12, 0, 0),
            amount=27 * 2 - 1,
            per_product=27,
            product_count=2,
            user_id=user.id,
            product_id=product.id,
        ),
    ]

    sql_session.add_all(transactions)
    sql_session.commit()

    pprint(product_price_log(sql_session, product))

    assert product_price(sql_session, product) == 27


def test_product_price_sold_out(sql_session: Session) -> None:
    user, product = insert_test_data(sql_session)

    transactions = [
        Transaction.add_product(
            amount=27 * 2 - 1,
            per_product=27,
            product_count=2,
            user_id=user.id,
            product_id=product.id,
        ),
        Transaction.buy_product(
            product_count=2,
            user_id=user.id,
            product_id=product.id,
        ),
    ]

    assign_times(transactions)

    sql_session.add_all(transactions)
    sql_session.commit()

    assert_id_order_similar_to_time_order(transactions)

    pprint(product_price_log(sql_session, product))

    assert product_price(sql_session, product) == 27


def test_product_price_interest(sql_session: Session) -> None:
    user, product = insert_test_data(sql_session)

    transactions = [
        Transaction.adjust_interest(
            interest_rate_percent=110,
            user_id=user.id,
        ),
        Transaction.add_product(
            amount=27 * 2 - 1,
            per_product=27,
            product_count=2,
            user_id=user.id,
            product_id=product.id,
        ),
    ]

    assign_times(transactions)

    sql_session.add_all(transactions)
    sql_session.commit()

    assert_id_order_similar_to_time_order(transactions)

    pprint(product_price_log(sql_session, product))

    product_price_ = product_price(sql_session, product)
    product_price_interest = product_price(sql_session, product, include_interest=True)

    assert product_price_ == 27
    assert product_price_interest == math.ceil(27 * 1.1)


def test_product_price_changing_interest(sql_session: Session) -> None:
    user, product = insert_test_data(sql_session)

    transactions = [
        Transaction.adjust_interest(
            interest_rate_percent=110,
            user_id=user.id,
        ),
        Transaction.add_product(
            amount=27 * 2 - 1,
            per_product=27,
            product_count=2,
            user_id=user.id,
            product_id=product.id,
        ),
        Transaction.adjust_interest(
            interest_rate_percent=120,
            user_id=user.id,
        ),
    ]

    assign_times(transactions)

    sql_session.add_all(transactions)
    sql_session.commit()

    assert_id_order_similar_to_time_order(transactions)

    pprint(product_price_log(sql_session, product))

    product_price_interest = product_price(sql_session, product, include_interest=True)
    assert product_price_interest == math.ceil(27 * 1.2)


def test_product_price_old_transaction(sql_session: Session) -> None:
    user, product = insert_test_data(sql_session)

    transactions = [
        Transaction.add_product(
            amount=27 * 2,
            per_product=27,
            product_count=2,
            user_id=user.id,
            product_id=product.id,
        ),
        # Price should be 27
        Transaction.add_product(
            amount=38 * 3,
            per_product=38,
            product_count=3,
            user_id=user.id,
            product_id=product.id,
        ),
        # price should be averaged upwards
    ]

    assign_times(transactions)

    sql_session.add_all(transactions)
    sql_session.commit()

    assert_id_order_similar_to_time_order(transactions)

    until_transaction = transactions[0]

    pprint(
        product_price_log(
            sql_session,
            product,
            until_transaction=until_transaction,
        ),
    )

    product_price_ = product_price(
        sql_session,
        product,
        until_transaction=until_transaction,
    )
    assert product_price_ == 27


# Price goes up and gets rounded up to the next integer
def test_product_price_round_up_from_below(sql_session: Session) -> None:
    user, product = insert_test_data(sql_session)

    transactions = [
        Transaction.add_product(
            amount=27 * 2,
            per_product=27,
            product_count=2,
            user_id=user.id,
            product_id=product.id,
        ),
        # Price should be 27
        Transaction.add_product(
            amount=38 * 3,
            per_product=38,
            product_count=3,
            user_id=user.id,
            product_id=product.id,
        ),
        # price should be averaged upwards
    ]

    assign_times(transactions)

    sql_session.add_all(transactions)
    sql_session.commit()

    assert_id_order_similar_to_time_order(transactions)

    pprint(product_price_log(sql_session, product))

    product_price_ = product_price(sql_session, product)
    assert product_price_ == math.ceil((27 * 2 + 38 * 3) / (2 + 3))


# Price goes down and gets rounded up to the next integer
def test_product_price_round_up_from_above(sql_session: Session) -> None:
    user, product = insert_test_data(sql_session)

    transactions = [
        Transaction.add_product(
            amount=27 * 2,
            per_product=27,
            product_count=2,
            user_id=user.id,
            product_id=product.id,
        ),
        # Price should be 27
        Transaction.add_product(
            amount=20 * 3,
            per_product=20,
            product_count=3,
            user_id=user.id,
            product_id=product.id,
        ),
        # price should be averaged downwards
    ]

    assign_times(transactions)

    sql_session.add_all(transactions)
    sql_session.commit()

    assert_id_order_similar_to_time_order(transactions)

    pprint(product_price_log(sql_session, product))

    product_price_ = product_price(sql_session, product)
    assert product_price_ == math.ceil((27 * 2 + 20 * 3) / (2 + 3))


def test_product_price_with_negative_stock_single_addition(sql_session: Session) -> None:
    user, product = insert_test_data(sql_session)

    transactions = [
        Transaction.add_product(
            amount=1,
            per_product=10,
            product_count=1,
            user_id=user.id,
            product_id=product.id,
        ),
        Transaction.buy_product(
            product_count=10,
            user_id=user.id,
            product_id=product.id,
        ),
        Transaction.add_product(
            amount=22,
            per_product=22,
            product_count=1,
            user_id=user.id,
            product_id=product.id,
        ),
    ]

    assign_times(transactions)

    sql_session.add_all(transactions)
    sql_session.commit()

    assert_id_order_similar_to_time_order(transactions)

    pprint(product_price_log(sql_session, product))

    # Stock went subzero, price should be the last added product price
    product1_price = product_price(sql_session, product)
    assert product1_price == 22


def test_product_price_with_negative_stock_multiple_additions(sql_session: Session) -> None:
    user, product = insert_test_data(sql_session)

    transactions = [
        Transaction.add_product(
            amount=1,
            per_product=10,
            product_count=1,
            user_id=user.id,
            product_id=product.id,
        ),
        Transaction.buy_product(
            product_count=10,
            user_id=user.id,
            product_id=product.id,
        ),
        Transaction.add_product(
            amount=22,
            per_product=22,
            product_count=1,
            user_id=user.id,
            product_id=product.id,
        ),
        Transaction.add_product(
            amount=29,
            per_product=29,
            product_count=2,
            user_id=user.id,
            product_id=product.id,
        ),
    ]

    assign_times(transactions)

    sql_session.add_all(transactions)
    sql_session.commit()

    assert_id_order_similar_to_time_order(transactions)

    pprint(product_price_log(sql_session, product))

    # Stock went subzero, price should be the last added product price
    product1_price = product_price(sql_session, product)
    assert product1_price == math.ceil(29)


def test_product_price_joint_transactions(sql_session: Session) -> None:
    user1, product = insert_test_data(sql_session)
    user2 = User("Test User 2")
    sql_session.add(user2)
    sql_session.commit()

    transactions = [
        Transaction.add_product(
            amount=30 * 3,
            per_product=30,
            product_count=3,
            user_id=user1.id,
            product_id=product.id,
        ),
        Transaction.add_product(
            amount=20 * 2,
            per_product=20,
            product_count=2,
            user_id=user2.id,
            product_id=product.id,
        ),
    ]

    assign_times(transactions)

    sql_session.add_all(transactions)
    sql_session.commit()

    assert_id_order_similar_to_time_order(transactions)

    product_price_ = product_price(sql_session, product)
    assert product_price_ == math.ceil((30 * 3 + 20 * 2) / (3 + 2))

    transactions += joint_buy_product(
        sql_session,
        instigator=user1,
        users=[user1, user2],
        product=product,
        product_count=2,
        time=transactions[-1].time + timedelta(seconds=1),
    )

    pprint(product_price_log(sql_session, product))

    old_product_price = product_price_
    product_price_ = product_price(sql_session, product)
    assert product_price_ == old_product_price, (
        "Joint buy transactions should not affect product price"
    )

    transactions = [
        Transaction.add_product(
            amount=25 * 4,
            per_product=25,
            product_count=4,
            user_id=user1.id,
            product_id=product.id,
            time=transactions[-1].time + timedelta(seconds=1),
        ),
    ]

    sql_session.add_all(transactions)
    sql_session.commit()

    pprint(product_price_log(sql_session, product))
    product_price_ = product_price(sql_session, product)

    # Expected state:
    # Added products:
    #   Count: 3 + 2 = 5, Price: (30 * 3 + 20 * 2) / 5 = 26
    # Joint bought products:
    #   Count: 5 - 2 = 3, Price: n/a (should not affect price)
    # Added products:
    #   Count: 3 + 4 = 7, Price: (26 * 3 + 25 * 4) / (3 + 4) = 25.57 -> 26

    assert product_price_ == math.ceil((26 * 3 + 25 * 4) / (3 + 4))


def test_product_price_until(sql_session: Session) -> None: ...

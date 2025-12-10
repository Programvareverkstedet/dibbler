import math
from datetime import datetime
from pprint import pprint

import pytest

from sqlalchemy.orm import Session

from dibbler.models import Product, Transaction, User
from dibbler.queries import user_balance, user_balance_log

# TODO: see if we can use pytest_runtest_makereport to print the "user_balance_log"s
#       only on failures instead of inlining it in every test function


def insert_test_data(sql_session: Session) -> tuple[User, Product]:
    user = User("Test User")
    product = Product("1234567890123", "Test Product")

    sql_session.add(user)
    sql_session.add(product)
    sql_session.commit()

    return user, product


def test_user_balance_no_transactions(sql_session: Session) -> None:
    user, _ = insert_test_data(sql_session)

    pprint(user_balance_log(sql_session, user))

    balance = user_balance(sql_session, user)

    assert balance == 0


def test_user_balance_basic_history(sql_session: Session) -> None:
    user, product = insert_test_data(sql_session)

    transactions = [
        Transaction.adjust_balance(
            time=datetime(2023, 10, 1, 10, 0, 0),
            user_id=user.id,
            amount=100,
        ),
        Transaction.add_product(
            time=datetime(2023, 10, 1, 10, 0, 1),
            user_id=user.id,
            product_id=product.id,
            amount=27,
            per_product=27,
            product_count=1,
        ),
    ]

    sql_session.add_all(transactions)
    sql_session.commit()

    pprint(user_balance_log(sql_session, user))

    balance = user_balance(sql_session, user)

    assert balance == 100 + 27


def test_user_balance_with_transfers(sql_session: Session) -> None:
    user1, product = insert_test_data(sql_session)

    user2 = User("Test User 2")
    sql_session.add(user2)
    sql_session.commit()

    transactions = [
        Transaction.adjust_balance(
            time=datetime(2023, 10, 1, 10, 0, 0),
            user_id=user1.id,
            amount=100,
        ),
        Transaction.transfer(
            time=datetime(2023, 10, 1, 10, 0, 1),
            user_id=user1.id,
            transfer_user_id=user2.id,
            amount=50,
        ),
        Transaction.transfer(
            time=datetime(2023, 10, 1, 10, 0, 2),
            user_id=user2.id,
            transfer_user_id=user1.id,
            amount=30,
        ),
    ]

    sql_session.add_all(transactions)
    sql_session.commit()

    pprint(user_balance_log(sql_session, user1))

    user1_balance = user_balance(sql_session, user1)
    assert user1_balance == 100 - 50 + 30

    pprint(user_balance_log(sql_session, user2))

    user2_balance = user_balance(sql_session, user2)
    assert user2_balance == 50 - 30


def test_user_balance_complex_history(sql_session: Session) -> None:
    raise NotImplementedError("This test is not implemented yet.")


def test_user_balance_penalty(sql_session: Session) -> None:
    user, product = insert_test_data(sql_session)

    transactions = [
        Transaction.add_product(
            time=datetime(2023, 10, 1, 10, 0, 0),
            user_id=user.id,
            product_id=product.id,
            amount=27,
            per_product=27,
            product_count=1,
        ),
        Transaction.adjust_balance(
            time=datetime(2023, 10, 1, 11, 0, 0),
            user_id=user.id,
            amount=-200,
        ),
        # Penalized, pays 2x the price (default penalty)
        Transaction.buy_product(
            time=datetime(2023, 10, 1, 12, 0, 0),
            user_id=user.id,
            product_id=product.id,
            product_count=1,
        ),
    ]
    sql_session.add_all(transactions)
    sql_session.commit()

    pprint(user_balance_log(sql_session, user))

    assert user_balance(sql_session, user) == 27 - 200 - (27 * 2)


def test_user_balance_changing_penalty(sql_session: Session) -> None:
    user, product = insert_test_data(sql_session)

    transactions = [
        Transaction.add_product(
            time=datetime(2023, 10, 1, 10, 0, 0),
            user_id=user.id,
            product_id=product.id,
            amount=27,
            per_product=27,
            product_count=1,
        ),
        Transaction.adjust_balance(
            time=datetime(2023, 10, 1, 11, 0, 0),
            user_id=user.id,
            amount=-200,
        ),
        # Penalized, pays 2x the price (default penalty)
        Transaction.buy_product(
            time=datetime(2023, 10, 1, 12, 0, 0),
            user_id=user.id,
            product_id=product.id,
            product_count=1,
        ),
        Transaction.adjust_penalty(
            time=datetime(2023, 10, 1, 13, 0, 0),
            user_id=user.id,
            penalty_multiplier_percent=300,
            penalty_threshold=-100,
        ),
        # Penalized, pays 3x the price
        Transaction.buy_product(
            time=datetime(2023, 10, 1, 14, 0, 0),
            user_id=user.id,
            product_id=product.id,
            product_count=1,
        ),
    ]

    sql_session.add_all(transactions)
    sql_session.commit()

    pprint(user_balance_log(sql_session, user))

    assert user_balance(sql_session, user) == 27 - 200 - (27 * 2) - (27 * 3)


def test_user_balance_interest(sql_session: Session) -> None:
    user, product = insert_test_data(sql_session)

    transactions = [
        Transaction.add_product(
            time=datetime(2023, 10, 1, 10, 0, 0),
            user_id=user.id,
            product_id=product.id,
            amount=27,
            per_product=27,
            product_count=1,
        ),
        Transaction.adjust_interest(
            time=datetime(2023, 10, 1, 11, 0, 0),
            user_id=user.id,
            interest_rate_percent=110,
        ),
        Transaction.buy_product(
            time=datetime(2023, 10, 1, 12, 0, 0),
            user_id=user.id,
            product_id=product.id,
            product_count=1,
        ),
    ]
    sql_session.add_all(transactions)
    sql_session.commit()

    pprint(user_balance_log(sql_session, user))

    assert user_balance(sql_session, user) == 27 - math.ceil(27 * 1.1)


def test_user_balance_changing_interest(sql_session: Session) -> None:
    user, product = insert_test_data(sql_session)

    transactions = [
        Transaction.add_product(
            time=datetime(2023, 10, 1, 10, 0, 0),
            user_id=user.id,
            product_id=product.id,
            amount=27 * 3,
            per_product=27,
            product_count=3,
        ),
        Transaction.adjust_interest(
            time=datetime(2023, 10, 1, 11, 0, 0),
            user_id=user.id,
            interest_rate_percent=110,
        ),
        # Pays 1.1x the price
        Transaction.buy_product(
            time=datetime(2023, 10, 1, 12, 0, 0),
            user_id=user.id,
            product_id=product.id,
            product_count=1,
        ),
        Transaction.adjust_interest(
            time=datetime(2023, 10, 1, 13, 0, 0),
            user_id=user.id,
            interest_rate_percent=120,
        ),
        # Pays 1.2x the price
        Transaction.buy_product(
            time=datetime(2023, 10, 1, 14, 0, 0),
            user_id=user.id,
            product_id=product.id,
            product_count=1,
        ),
    ]
    sql_session.add_all(transactions)
    sql_session.commit()

    pprint(user_balance_log(sql_session, user))

    assert user_balance(sql_session, user) == 27 * 3 - math.ceil(27 * 1.1) - math.ceil(27 * 1.2)


def test_user_balance_penalty_interest_combined(sql_session: Session) -> None:
    user, product = insert_test_data(sql_session)

    transactions = [
        Transaction.add_product(
            time=datetime(2023, 10, 1, 10, 0, 0),
            user_id=user.id,
            product_id=product.id,
            amount=27,
            per_product=27,
            product_count=1,
        ),
        Transaction.adjust_interest(
            time=datetime(2023, 10, 1, 11, 0, 0),
            user_id=user.id,
            interest_rate_percent=110,
        ),
        Transaction.adjust_balance(
            time=datetime(2023, 10, 1, 12, 0, 0),
            user_id=user.id,
            amount=-200,
        ),
        # Penalized, pays 2x the price (default penalty)
        # Pays 1.1x the price
        Transaction.buy_product(
            time=datetime(2023, 10, 1, 13, 0, 0),
            user_id=user.id,
            product_id=product.id,
            product_count=1,
        ),
    ]
    sql_session.add_all(transactions)
    sql_session.commit()

    pprint(user_balance_log(sql_session, user))

    assert user_balance(sql_session, user) == (27 - 200 - math.ceil(27 * 2 * 1.1))


@pytest.mark.skip(reason="Not yet implemented")
def test_user_balance_joint_transactions(sql_session: Session): ...


@pytest.mark.skip(reason="Not yet implemented")
def test_user_balance_joint_transactions_interest(sql_session: Session): ...


@pytest.mark.skip(reason="Not yet implemented")
def test_user_balance_joint_transactions_changing_interest(sql_session: Session): ...


@pytest.mark.skip(reason="Not yet implemented")
def test_user_balance_joint_transactions_penalty(sql_session: Session): ...


@pytest.mark.skip(reason="Not yet implemented")
def test_user_balance_joint_transactions_changing_penalty(sql_session: Session): ...


@pytest.mark.skip(reason="Not yet implemented")
def test_user_balance_joint_transactions_penalty_interest_combined(sql_session: Session): ...


@pytest.mark.skip(reason="Not yet implemented")
def test_user_balance_until(sql_session: Session): ...


@pytest.mark.skip(reason="Not yet implemented")
def test_user_balance_throw_away_products(sql_session: Session): ...

import math
from datetime import datetime, timedelta
from pprint import pprint

import pytest
from sqlalchemy.orm import Session

from dibbler.models import Product, Transaction, User
from dibbler.models.Transaction import (
    DEFAULT_INTEREST_RATE_PERCENT,
    DEFAULT_PENALTY_MULTIPLIER_PERCENT,
)
from dibbler.queries import joint_buy_product, user_balance, user_balance_log
from dibbler.queries.user_balance import _joint_transaction_query, _non_joint_transaction_query
from tests.helpers import assert_id_order_similar_to_time_order, assign_times

# TODO: see if we can use pytest_runtest_makereport to print the "user_balance_log"s
#       only on failures instead of inlining it in every test function


def insert_test_data(sql_session: Session) -> tuple[User, User, User, Product]:
    user = User("Test User")
    user2 = User("Test User 2")
    user3 = User("Test User 3")
    product = Product("1234567890123", "Test Product")

    sql_session.add_all([user, user2, user3, product])
    sql_session.commit()

    return user, user2, user3, product


# NOTE: see economics spec
def _product_cost(
    per_product: int,
    product_count: int,
    interest_rate_percent: int = DEFAULT_INTEREST_RATE_PERCENT,
    apply_penalty: bool = False,
    penalty_multiplier_percent: int = DEFAULT_PENALTY_MULTIPLIER_PERCENT,
    joint_shares: int = 1,
    joint_total_shares: int = 1,
) -> int:
    base_cost: float = per_product * product_count * joint_shares / joint_total_shares
    added_interest: float = base_cost * ((interest_rate_percent - 100) / 100)

    penalty: float = 0.0
    if apply_penalty:
        penalty: float = base_cost * ((penalty_multiplier_percent - 100) / 100)

    total_cost: int = math.ceil(base_cost + added_interest + penalty)

    return total_cost


def test_non_joint_transaction_query(sql_session) -> None:
    user1, user2, user3, product = insert_test_data(sql_session)

    transactions = [
        Transaction.adjust_balance(
            user_id=user1.id,
            amount=100,
        ),
        Transaction.adjust_balance(
            user_id=user2.id,
            amount=50,
        ),
        Transaction.add_product(
            user_id=user2.id,
            amount=70,
            product_id=product.id,
            product_count=3,
            per_product=30,
        ),
        Transaction.transfer(
            user_id=user1.id,
            transfer_user_id=user2.id,
            amount=50,
        ),
        Transaction.transfer(
            user_id=user2.id,
            transfer_user_id=user3.id,
            amount=30,
        ),
    ]

    assign_times(transactions)

    sql_session.add_all(transactions)
    sql_session.commit()

    assert_id_order_similar_to_time_order(transactions)

    t = transactions

    result = {
        row[0]
        for row in sql_session.execute(
            _non_joint_transaction_query(
                user_id=user1.id,
                use_cache=False,
            ),
        ).all()
    }
    assert result == {t[0].id, t[3].id}

    result = {
        row[0]
        for row in sql_session.execute(
            _non_joint_transaction_query(
                user_id=user2.id,
                use_cache=False,
            ),
        ).all()
    }
    assert result == {
        t[1].id,
        t[2].id,
        t[3].id,
        t[4].id,
    }

    result = {
        row[0]
        for row in sql_session.execute(
            _non_joint_transaction_query(
                user_id=user3.id,
                use_cache=False,
            ),
        ).all()
    }
    assert result == {t[4].id}


def test_joint_transaction_query(sql_session: Session) -> None:
    user1, user2, user3, product = insert_test_data(sql_session)

    j1 = joint_buy_product(
        sql_session,
        product=product,
        product_count=3,
        instigator=user1,
        users=[user1, user2],
    )

    j2 = joint_buy_product(
        sql_session,
        product=product,
        product_count=2,
        instigator=user1,
        users=[user1, user1, user2],
        time=j1[-1].time + timedelta(minutes=1),
    )

    j3 = joint_buy_product(
        sql_session,
        product=product,
        product_count=2,
        instigator=user1,
        users=[user1, user3, user3],
        time=j2[-1].time + timedelta(minutes=1),
    )

    j4 = joint_buy_product(
        sql_session,
        product=product,
        product_count=2,
        instigator=user2,
        users=[user2, user3, user3],
        time=j3[-1].time + timedelta(minutes=1),
    )

    assert_id_order_similar_to_time_order(j1 + j2 + j3 + j4)

    result = set(
        sql_session.execute(
            _joint_transaction_query(
                user_id=user1.id,
                use_cache=False,
            ),
        ).all(),
    )
    assert result == {
        (j1[0].id, 1, 2),
        (j2[0].id, 2, 3),
        (j3[0].id, 1, 3),
    }

    result = set(
        sql_session.execute(
            _joint_transaction_query(
                user_id=user2.id,
                use_cache=False,
            ),
        ).all(),
    )
    assert result == {
        (j1[0].id, 1, 2),
        (j2[0].id, 1, 3),
        (j4[0].id, 1, 3),
    }

    result = set(
        sql_session.execute(
            _joint_transaction_query(
                user_id=user3.id,
                use_cache=False,
            ),
        ).all(),
    )
    assert result == {
        (j3[0].id, 2, 3),
        (j4[0].id, 2, 3),
    }


def test_user_balance_no_transactions(sql_session: Session) -> None:
    user, *_ = insert_test_data(sql_session)

    pprint(user_balance_log(sql_session, user))

    balance = user_balance(sql_session, user)

    assert balance == 0


def test_user_balance_basic_history(sql_session: Session) -> None:
    user, _, _, product = insert_test_data(sql_session)

    transactions = [
        Transaction.adjust_balance(
            user_id=user.id,
            amount=100,
        ),
        Transaction.add_product(
            user_id=user.id,
            product_id=product.id,
            amount=27,
            per_product=27,
            product_count=1,
        ),
    ]

    assign_times(transactions)

    sql_session.add_all(transactions)
    sql_session.commit()

    assert_id_order_similar_to_time_order(transactions)

    pprint(user_balance_log(sql_session, user))

    balance = user_balance(sql_session, user)

    assert balance == 100 + 27


def test_user_balance_with_transfers(sql_session: Session) -> None:
    user1, user2, _, _ = insert_test_data(sql_session)

    transactions = [
        Transaction.adjust_balance(
            user_id=user1.id,
            amount=100,
        ),
        Transaction.transfer(
            user_id=user1.id,
            transfer_user_id=user2.id,
            amount=50,
        ),
        Transaction.transfer(
            user_id=user2.id,
            transfer_user_id=user1.id,
            amount=30,
        ),
    ]

    assign_times(transactions)

    sql_session.add_all(transactions)
    sql_session.commit()

    assert_id_order_similar_to_time_order(transactions)

    pprint(user_balance_log(sql_session, user1))

    user1_balance = user_balance(sql_session, user1)
    assert user1_balance == 100 - 50 + 30

    pprint(user_balance_log(sql_session, user2))

    user2_balance = user_balance(sql_session, user2)
    assert user2_balance == 50 - 30


def test_user_balance_penalty(sql_session: Session) -> None:
    user, _, _, product = insert_test_data(sql_session)

    transactions = [
        Transaction.add_product(
            user_id=user.id,
            product_id=product.id,
            amount=27,
            per_product=27,
            product_count=1,
        ),
        Transaction.adjust_balance(
            user_id=user.id,
            amount=-200,
        ),
        # Penalized, pays 2x the price (default penalty)
        Transaction.buy_product(
            user_id=user.id,
            product_id=product.id,
            product_count=1,
        ),
    ]

    assign_times(transactions)

    sql_session.add_all(transactions)
    sql_session.commit()

    assert_id_order_similar_to_time_order(transactions)

    pprint(user_balance_log(sql_session, user))

    assert user_balance(sql_session, user) == 27 - 200 - _product_cost(27, 1, apply_penalty=True)


def test_user_balance_changing_penalty(sql_session: Session) -> None:
    user, _, _, product = insert_test_data(sql_session)

    transactions = [
        Transaction.add_product(
            user_id=user.id,
            product_id=product.id,
            amount=27,
            per_product=27,
            product_count=1,
        ),
        Transaction.adjust_balance(
            user_id=user.id,
            amount=-200,
        ),
        # Penalized, pays 2x the price (default penalty)
        Transaction.buy_product(
            user_id=user.id,
            product_id=product.id,
            product_count=1,
        ),
        Transaction.adjust_penalty(
            user_id=user.id,
            penalty_multiplier_percent=300,
            penalty_threshold=-100,
        ),
        # Penalized, pays 3x the price
        Transaction.buy_product(
            user_id=user.id,
            product_id=product.id,
            product_count=1,
        ),
    ]

    assign_times(transactions)

    sql_session.add_all(transactions)
    sql_session.commit()

    assert_id_order_similar_to_time_order(transactions)

    pprint(user_balance_log(sql_session, user))

    assert user_balance(sql_session, user) == (
        27
        - 200
        - _product_cost(27, 1, apply_penalty=True)
        - _product_cost(27, 1, apply_penalty=True, penalty_multiplier_percent=300)
    )


def test_user_balance_interest(sql_session: Session) -> None:
    user, _, _, product = insert_test_data(sql_session)

    transactions = [
        Transaction.add_product(
            user_id=user.id,
            product_id=product.id,
            amount=27,
            per_product=27,
            product_count=1,
        ),
        Transaction.adjust_interest(
            user_id=user.id,
            interest_rate_percent=110,
        ),
        Transaction.buy_product(
            user_id=user.id,
            product_id=product.id,
            product_count=1,
        ),
    ]

    assign_times(transactions)

    sql_session.add_all(transactions)
    sql_session.commit()

    assert_id_order_similar_to_time_order(transactions)

    pprint(user_balance_log(sql_session, user))

    assert user_balance(sql_session, user) == 27 - _product_cost(27, 1, interest_rate_percent=110)


def test_user_balance_changing_interest(sql_session: Session) -> None:
    user, _, _, product = insert_test_data(sql_session)

    transactions = [
        Transaction.add_product(
            user_id=user.id,
            product_id=product.id,
            amount=27 * 3,
            per_product=27,
            product_count=3,
        ),
        Transaction.adjust_interest(
            user_id=user.id,
            interest_rate_percent=110,
        ),
        # Pays 1.1x the price
        Transaction.buy_product(
            user_id=user.id,
            product_id=product.id,
            product_count=1,
        ),
        Transaction.adjust_interest(
            user_id=user.id,
            interest_rate_percent=120,
        ),
        # Pays 1.2x the price
        Transaction.buy_product(
            user_id=user.id,
            product_id=product.id,
            product_count=1,
        ),
    ]

    assign_times(transactions)

    sql_session.add_all(transactions)
    sql_session.commit()

    assert_id_order_similar_to_time_order(transactions)

    pprint(user_balance_log(sql_session, user))

    assert user_balance(sql_session, user) == (
        27 * 3
        - _product_cost(27, 1, interest_rate_percent=110)
        - _product_cost(27, 1, interest_rate_percent=120)
    )


def test_user_balance_penalty_interest_combined(sql_session: Session) -> None:
    user, _, _, product = insert_test_data(sql_session)

    transactions = [
        Transaction.add_product(
            user_id=user.id,
            product_id=product.id,
            amount=27,
            per_product=27,
            product_count=1,
        ),
        Transaction.adjust_interest(
            user_id=user.id,
            interest_rate_percent=110,
        ),
        Transaction.adjust_balance(
            user_id=user.id,
            amount=-200,
        ),
        # Penalized, pays 2x the price (default penalty)
        # Pays 1.1x the price
        Transaction.buy_product(
            user_id=user.id,
            product_id=product.id,
            product_count=1,
        ),
    ]

    assign_times(transactions)

    sql_session.add_all(transactions)
    sql_session.commit()

    assert_id_order_similar_to_time_order(transactions)

    pprint(user_balance_log(sql_session, user))

    assert user_balance(sql_session, user) == (
        27
        - 200
        - _product_cost(
            27,
            1,
            interest_rate_percent=110,
            apply_penalty=True,
        )
    )


def test_user_balance_joint_transaction_single_user(sql_session: Session) -> None:
    user, _, _, product = insert_test_data(sql_session)

    transactions = [
        Transaction.add_product(
            time=datetime(2023, 10, 1, 10, 0, 0),
            user_id=user.id,
            product_id=product.id,
            amount=27 * 3,
            per_product=27,
            product_count=3,
        ),
    ]
    sql_session.add_all(transactions)
    sql_session.commit()

    joint_buy_product(
        sql_session,
        instigator=user,
        users=[user],
        product=product,
        product_count=2,
        time=transactions[-1].time + timedelta(minutes=1),
    )

    pprint(user_balance_log(sql_session, user))

    assert user_balance(sql_session, user) == (
        (27 * 3)
        - _product_cost(
            27,
            2,
            joint_shares=1,
            joint_total_shares=1,
        )
    )


def test_user_balance_joint_transactions_multiple_users(sql_session: Session) -> None:
    user, user2, user3, product = insert_test_data(sql_session)

    transactions = [
        Transaction.add_product(
            time=datetime(2023, 10, 1, 10, 0, 0),
            user_id=user.id,
            product_id=product.id,
            amount=27 * 3,
            per_product=27,
            product_count=3,
        ),
    ]
    sql_session.add_all(transactions)
    sql_session.commit()

    joint_buy_product(
        sql_session,
        instigator=user,
        users=[user, user2, user3],
        product=product,
        product_count=2,
        time=transactions[-1].time + timedelta(minutes=1),
    )

    pprint(user_balance_log(sql_session, user))

    assert user_balance(sql_session, user) == (
        (27 * 3)
        - _product_cost(
            27,
            2,
            joint_shares=1,
            joint_total_shares=3,
        )
    )


def test_user_balance_joint_transactions_multiple_times_self(sql_session: Session) -> None:
    user, user2, _, product = insert_test_data(sql_session)

    transactions = [
        Transaction.add_product(
            time=datetime(2023, 10, 1, 10, 0, 0),
            user_id=user.id,
            product_id=product.id,
            amount=27 * 3,
            per_product=27,
            product_count=3,
        ),
    ]
    sql_session.add_all(transactions)
    sql_session.commit()

    joint_buy_product(
        sql_session,
        instigator=user,
        users=[user, user, user2],
        product=product,
        product_count=2,
        time=transactions[-1].time + timedelta(minutes=1),
    )

    pprint(user_balance_log(sql_session, user))

    assert user_balance(sql_session, user) == (
        (27 * 3)
        - _product_cost(
            27,
            2,
            joint_shares=2,
            joint_total_shares=3,
        )
    )


def test_user_balance_joint_transactions_interest(sql_session: Session) -> None:
    user, user2, _, product = insert_test_data(sql_session)

    transactions = [
        Transaction.add_product(
            user_id=user.id,
            product_id=product.id,
            amount=27 * 3,
            per_product=27,
            product_count=3,
        ),
        Transaction.adjust_interest(
            user_id=user.id,
            interest_rate_percent=110,
        ),
    ]

    assign_times(transactions)

    sql_session.add_all(transactions)
    sql_session.commit()

    transactions += joint_buy_product(
        sql_session,
        instigator=user,
        users=[user, user2],
        product=product,
        product_count=2,
        time=transactions[-1].time + timedelta(minutes=1),
    )

    assert_id_order_similar_to_time_order(transactions)

    pprint(user_balance_log(sql_session, user))

    assert user_balance(sql_session, user) == (
        (27 * 3)
        - _product_cost(
            27,
            2,
            joint_shares=1,
            joint_total_shares=2,
            interest_rate_percent=110,
        )
    )


def test_user_balance_joint_transactions_changing_interest(sql_session: Session) -> None:
    user, user2, _, product = insert_test_data(sql_session)

    transactions = [
        Transaction.add_product(
            user_id=user.id,
            product_id=product.id,
            amount=27 * 4,
            per_product=27,
            product_count=4,
        ),
        # Pays 1.1x the price
        Transaction.adjust_interest(
            user_id=user.id,
            interest_rate_percent=110,
        ),
    ]

    assign_times(transactions)

    sql_session.add_all(transactions)
    sql_session.commit()

    transactions += joint_buy_product(
        sql_session,
        instigator=user,
        users=[user, user2],
        product=product,
        product_count=2,
        time=transactions[-1].time + timedelta(minutes=15),
    )

    transactions += [
        # Pays 1.2x the price
        Transaction.adjust_interest(
            time=transactions[-1].time + timedelta(minutes=15),
            user_id=user.id,
            interest_rate_percent=120,
        ),
    ]
    sql_session.add_all(transactions)
    sql_session.commit()

    transactions += joint_buy_product(
        sql_session,
        instigator=user,
        users=[user, user2],
        product=product,
        product_count=1,
        time=transactions[-1].time + timedelta(minutes=15),
    )

    assert_id_order_similar_to_time_order(transactions)

    pprint(user_balance_log(sql_session, user))

    assert user_balance(sql_session, user) == (
        (27 * 4)
        - _product_cost(
            27,
            2,
            joint_shares=1,
            joint_total_shares=2,
            interest_rate_percent=110,
        )
        - _product_cost(
            27,
            1,
            joint_shares=1,
            joint_total_shares=2,
            interest_rate_percent=120,
        )
    )


def test_user_balance_joint_transactions_penalty(sql_session: Session) -> None:
    user, user2, _, product = insert_test_data(sql_session)

    transactions = [
        Transaction.add_product(
            user_id=user.id,
            product_id=product.id,
            amount=27 * 3,
            per_product=27,
            product_count=3,
        ),
        Transaction.adjust_balance(
            user_id=user.id,
            amount=-200,
        ),
    ]

    assign_times(transactions)

    sql_session.add_all(transactions)
    sql_session.commit()

    transactions += joint_buy_product(
        sql_session,
        instigator=user,
        users=[user, user2],
        product=product,
        product_count=2,
        time=transactions[-1].time + timedelta(minutes=15),
    )

    assert_id_order_similar_to_time_order(transactions)

    pprint(user_balance_log(sql_session, user))

    assert user_balance(sql_session, user) == (
        (27 * 3)
        - 200
        - _product_cost(
            27,
            2,
            joint_shares=1,
            joint_total_shares=2,
            apply_penalty=True,
        )
    )


def test_user_balance_joint_transactions_changing_penalty(sql_session: Session) -> None:
    user, user2, _, product = insert_test_data(sql_session)

    transactions = [
        Transaction.add_product(
            user_id=user.id,
            product_id=product.id,
            amount=27 * 3,
            per_product=27,
            product_count=3,
        ),
        Transaction.adjust_balance(
            user_id=user.id,
            amount=-200,
        ),
    ]

    assign_times(transactions)

    sql_session.add_all(transactions)
    sql_session.commit()

    transactions += joint_buy_product(
        sql_session,
        instigator=user,
        users=[user, user2],
        product=product,
        product_count=2,
        time=transactions[-1].time + timedelta(minutes=15),
    )

    transactions += [
        Transaction.adjust_penalty(
            time=transactions[-1].time + timedelta(minutes=30),
            user_id=user.id,
            penalty_multiplier_percent=300,
            penalty_threshold=-100,
        ),
    ]

    sql_session.add_all(transactions)
    sql_session.commit()

    transactions += joint_buy_product(
        sql_session,
        instigator=user,
        users=[user, user2],
        product=product,
        product_count=1,
        time=transactions[-1].time + timedelta(minutes=45),
    )

    assert_id_order_similar_to_time_order(transactions)

    pprint(user_balance_log(sql_session, user))

    assert user_balance(sql_session, user) == (
        (27 * 3)
        - 200
        - _product_cost(
            27,
            2,
            joint_shares=1,
            joint_total_shares=2,
            apply_penalty=True,
        )
        - _product_cost(
            27,
            1,
            joint_shares=1,
            joint_total_shares=2,
            apply_penalty=True,
            penalty_multiplier_percent=300,
        )
    )


def test_user_balance_joint_transactions_penalty_interest_combined(
    sql_session: Session,
) -> None:
    user, user2, _, product = insert_test_data(sql_session)

    transactions = [
        Transaction.add_product(
            user_id=user.id,
            product_id=product.id,
            amount=27 * 3,
            per_product=27,
            product_count=3,
        ),
        Transaction.adjust_interest(
            user_id=user.id,
            interest_rate_percent=110,
        ),
        Transaction.adjust_balance(
            user_id=user.id,
            amount=-200,
        ),
    ]

    assign_times(transactions)

    sql_session.add_all(transactions)
    sql_session.commit()

    transactions += joint_buy_product(
        sql_session,
        instigator=user,
        users=[user, user2],
        product=product,
        product_count=2,
        time=transactions[-1].time + timedelta(minutes=15),
    )

    pprint(user_balance_log(sql_session, user))

    assert user_balance(sql_session, user) == (
        (27 * 3)
        - 200
        - _product_cost(
            27,
            2,
            joint_shares=1,
            joint_total_shares=2,
            interest_rate_percent=110,
            apply_penalty=True,
        )
    )


def test_user_balance_until_time(sql_session: Session) -> None:
    user, _, _, product = insert_test_data(sql_session)

    transactions = [
        Transaction.adjust_balance(
            user_id=user.id,
            amount=100,
        ),
        Transaction.add_product(
            user_id=user.id,
            product_id=product.id,
            amount=27,
            per_product=27,
            product_count=1,
        ),
        Transaction.adjust_balance(
            user_id=user.id,
            amount=50,
        ),
    ]

    assign_times(transactions)

    sql_session.add_all(transactions)
    sql_session.commit()

    pprint(
        user_balance_log(
            sql_session,
            user,
            until_time=transactions[1].time + timedelta(seconds=30),
        ),
    )

    balance = user_balance(
        sql_session,
        user,
        until_time=transactions[1].time + timedelta(seconds=30),
    )

    assert balance == 100 + 27


def test_user_balance_until_transaction(sql_session: Session) -> None:
    user, _, _, product = insert_test_data(sql_session)

    transactions = [
        Transaction.adjust_balance(
            user_id=user.id,
            amount=100,
        ),
        Transaction.add_product(
            user_id=user.id,
            product_id=product.id,
            amount=27,
            per_product=27,
            product_count=1,
        ),
        Transaction.adjust_balance(
            user_id=user.id,
            amount=50,
        ),
    ]

    assign_times(transactions)

    sql_session.add_all(transactions)
    sql_session.commit()

    until_transaction = transactions[1]

    pprint(
        user_balance_log(
            sql_session,
            user,
            until_transaction=until_transaction,
        ),
    )

    balance = user_balance(
        sql_session,
        user,
        until_transaction=until_transaction,
    )

    assert balance == 100 + 27


@pytest.mark.skip(reason="Not yet implemented")
def test_user_balance_throw_away_products(sql_session: Session) -> None: ...

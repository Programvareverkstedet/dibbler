from datetime import datetime, timedelta

import pytest
from sqlalchemy.orm import Session

from dibbler.models import (
    Product,
    Transaction,
    TransactionType,
    User,
)
from dibbler.queries import transaction_log
from tests.helpers import assert_id_order_similar_to_time_order, assign_times


def insert_test_data(sql_session: Session) -> tuple[User, User, Product, Product]:
    user1 = User("Test User 1")
    user2 = User("Test User 2")

    product1 = Product("1234567890123", "Test Product 1")
    product2 = Product("9876543210987", "Test Product 2")
    sql_session.add_all([user1, user2, product1, product2])
    sql_session.commit()

    return user1, user2, product1, product2


def insert_default_test_transactions(
    sql_session: Session,
    user1: User,
    user2: User,
    product1: Product,
    product2: Product,
) -> list[Transaction]:
    transactions = [
        Transaction.adjust_balance(
            amount=100,
            user_id=user1.id,
        ),
        Transaction.adjust_balance(
            amount=50,
            user_id=user2.id,
        ),
        Transaction.adjust_balance(
            amount=-50,
            user_id=user1.id,
        ),
        Transaction.add_product(
            amount=27 * 2,
            per_product=27,
            product_count=2,
            user_id=user1.id,
            product_id=product1.id,
        ),
        Transaction.buy_product(
            product_count=1,
            user_id=user2.id,
            product_id=product2.id,
        ),
        Transaction.add_product(
            amount=15 * 1,
            per_product=15,
            product_count=1,
            user_id=user2.id,
            product_id=product2.id,
        ),
        Transaction.transfer(
            amount=30,
            user_id=user1.id,
            transfer_user_id=user2.id,
        ),
    ]

    assign_times(transactions)

    sql_session.add_all(transactions)
    sql_session.commit()

    assert_id_order_similar_to_time_order(transactions)

    return transactions


def test_transaction_log_invalid_limit(sql_session: Session) -> None:
    with pytest.raises(ValueError):
        transaction_log(sql_session, limit=0)

    with pytest.raises(ValueError):
        transaction_log(sql_session, limit=-1)


def test_transaction_log_uninitialized_user(sql_session: Session) -> None:
    user = User("Uninitialized User")

    with pytest.raises(ValueError):
        transaction_log(sql_session, user=user)


def test_transaction_log_uninitialized_product(sql_session: Session) -> None:
    product = Product("1234567890123", "Uninitialized Product")

    with pytest.raises(ValueError):
        transaction_log(sql_session, product=product)


def test_transaction_log_uninitialized_after_until_transaction(sql_session: Session) -> None:
    user, user2, product, product2 = insert_test_data(sql_session)
    insert_default_test_transactions(sql_session, user, user2, product, product2)

    uninitialized_transaction = Transaction.adjust_balance(
        time=datetime(2023, 10, 1, 10, 0, 0),
        amount=100,
        user_id=user.id,
    )

    with pytest.raises(ValueError):
        transaction_log(
            sql_session,
            user=user,
            after_transaction=uninitialized_transaction,
        )

    with pytest.raises(ValueError):
        transaction_log(
            sql_session,
            user=user,
            until_transaction=uninitialized_transaction,
        )


def test_transaction_log_product_and_user_not_allowed(sql_session: Session) -> None:
    user, user2, product, product2 = insert_test_data(sql_session)
    insert_default_test_transactions(sql_session, user, user2, product, product2)

    with pytest.raises(ValueError):
        transaction_log(
            sql_session,
            user=user,
            product=product,
        )


def test_transaction_log_until_datetime_and_transaction_id_not_allowed(
    sql_session: Session,
) -> None:
    user, user2, product, product2 = insert_test_data(sql_session)
    insert_default_test_transactions(sql_session, user, user2, product, product2)

    trx = Transaction.adjust_balance(
        time=datetime(2023, 10, 1, 10, 0, 0),
        amount=100,
        user_id=user.id,
    )
    sql_session.add(trx)
    sql_session.commit()

    with pytest.raises(ValueError):
        transaction_log(
            sql_session,
            user=user,
            until_time=datetime(2023, 10, 1, 11, 0, 0),
            until_transaction=trx,
        )


def test_transaction_log_after_datetime_and_transaction_id_not_allowed(
    sql_session: Session,
) -> None:
    user, user2, product, product2 = insert_test_data(sql_session)
    insert_default_test_transactions(sql_session, user, user2, product, product2)

    trx = Transaction.adjust_balance(
        time=datetime(2023, 10, 1, 10, 0, 0),
        amount=100,
        user_id=user.id,
    )
    sql_session.add(trx)
    sql_session.commit()

    with pytest.raises(ValueError):
        transaction_log(
            sql_session,
            user=user,
            after_time=datetime(2023, 10, 1, 15, 0, 0),
            after_transaction=trx,
        )


def test_user_transactions_no_transactions(sql_session: Session) -> None:
    insert_test_data(sql_session)

    transactions = transaction_log(sql_session)

    assert len(transactions) == 0


def test_transaction_log_basic(sql_session: Session) -> None:
    user, user2, product, product2 = insert_test_data(sql_session)
    insert_default_test_transactions(sql_session, user, user2, product, product2)

    assert len(transaction_log(sql_session)) == 7


def test_transaction_log_filtered_by_user(sql_session: Session) -> None:
    user, user2, product, product2 = insert_test_data(sql_session)
    insert_default_test_transactions(sql_session, user, user2, product, product2)

    assert len(transaction_log(sql_session, user=user)) == 4
    assert len(transaction_log(sql_session, user=user2)) == 3


def test_transaction_log_filtered_by_product(sql_session: Session) -> None:
    user, user2, product, product2 = insert_test_data(sql_session)
    insert_default_test_transactions(sql_session, user, user2, product, product2)

    assert len(transaction_log(sql_session, product=product)) == 1
    assert len(transaction_log(sql_session, product=product2)) == 2


def test_transaction_log_after_datetime(sql_session: Session) -> None:
    user, user2, product, product2 = insert_test_data(sql_session)
    transactions = insert_default_test_transactions(sql_session, user, user2, product, product2)

    assert (
        len(
            transaction_log(
                sql_session,
                after_time=transactions[2].time,
            ),
        )
        == len(transactions) - 2
    )


def test_transaction_log_after_datetime_no_transactions(sql_session: Session) -> None:
    user, user2, product, product2 = insert_test_data(sql_session)
    transactions = insert_default_test_transactions(sql_session, user, user2, product, product2)
    assert (
        len(
            transaction_log(
                sql_session,
                after_time=transactions[-1].time + timedelta(seconds=1),
            ),
        )
        == 0
    )


def test_transaction_log_after_datetime_exclusive(sql_session: Session) -> None:
    user, user2, product, product2 = insert_test_data(sql_session)
    transactions = insert_default_test_transactions(sql_session, user, user2, product, product2)

    assert (
        len(
            transaction_log(
                sql_session,
                after_time=transactions[2].time,
                after_inclusive=False,
            ),
        )
        == len(transactions) - 3
    )


def test_transaction_log_after_transaction_id(sql_session: Session) -> None:
    user, user2, product, product2 = insert_test_data(sql_session)
    transactions = insert_default_test_transactions(sql_session, user, user2, product, product2)

    first_transaction = transactions[0]

    assert len(
        transaction_log(
            sql_session,
            after_transaction=first_transaction,
        ),
    ) == len(transactions)


def test_transaction_log_after_transaction_id_one_transaction(sql_session: Session) -> None:
    user, user2, product, product2 = insert_test_data(sql_session)
    transactions = insert_default_test_transactions(sql_session, user, user2, product, product2)

    last_transaction = transactions[-1]

    assert (
        len(
            transaction_log(
                sql_session,
                after_transaction=last_transaction,
            ),
        )
        == 1
    )


def test_transaction_log_after_transaction_id_exclusive(sql_session: Session) -> None:
    user, user2, product, product2 = insert_test_data(sql_session)
    transactions = insert_default_test_transactions(sql_session, user, user2, product, product2)

    third_transaction = transactions[2]

    assert (
        len(
            transaction_log(
                sql_session,
                after_transaction=third_transaction,
                after_inclusive=False,
            ),
        )
        == len(transactions) - 3
    )


def test_transaction_log_until_datetime(sql_session: Session) -> None:
    user, user2, product, product2 = insert_test_data(sql_session)
    transactions = insert_default_test_transactions(sql_session, user, user2, product, product2)

    assert (
        len(
            transaction_log(
                sql_session,
                until_time=transactions[-3].time,
            ),
        )
        == len(transactions) - 2
    )


def test_transaction_log_until_datetime_no_transactions(sql_session: Session) -> None:
    user, user2, product, product2 = insert_test_data(sql_session)
    transactions = insert_default_test_transactions(sql_session, user, user2, product, product2)

    assert (
        len(
            transaction_log(
                sql_session,
                until_time=transactions[0].time - timedelta(seconds=1),
            ),
        )
        == 0
    )


def test_transaction_log_until_datetime_exclusive(sql_session: Session) -> None:
    user, user2, product, product2 = insert_test_data(sql_session)
    transactions = insert_default_test_transactions(sql_session, user, user2, product, product2)

    assert (
        len(
            transaction_log(
                sql_session,
                until_time=transactions[-3].time,
                until_inclusive=False,
            ),
        )
        == len(transactions) - 3
    )


def test_transaction_log_until_transaction(sql_session: Session) -> None:
    user, user2, product, product2 = insert_test_data(sql_session)
    transactions = insert_default_test_transactions(sql_session, user, user2, product, product2)

    last_transaction = transactions[-3]

    assert (
        len(
            transaction_log(
                sql_session,
                until_transaction=last_transaction,
            ),
        )
        == len(transactions) - 2
    )


def test_transaction_log_until_transaction_one_transaction(sql_session: Session) -> None:
    user, user2, product, product2 = insert_test_data(sql_session)
    transactions = insert_default_test_transactions(sql_session, user, user2, product, product2)

    first_transaction = transactions[0]

    assert (
        len(
            transaction_log(
                sql_session,
                until_transaction=first_transaction,
            ),
        )
        == 1
    )


def test_transaction_log_until_transaction_exclusive(sql_session: Session) -> None:
    user, user2, product, product2 = insert_test_data(sql_session)
    transactions = insert_default_test_transactions(sql_session, user, user2, product, product2)

    last_transaction = transactions[-3]

    assert (
        len(
            transaction_log(
                sql_session,
                until_transaction=last_transaction,
                until_inclusive=False,
            ),
        )
        == len(transactions) - 3
    )


def test_transaction_log_after_until_datetime_illegal_order(sql_session: Session) -> None:
    user, user2, product, product2 = insert_test_data(sql_session)
    transactions = insert_default_test_transactions(sql_session, user, user2, product, product2)

    second_transaction = transactions[1]
    fifth_transaction = transactions[4]

    with pytest.raises(ValueError):
        transaction_log(
            sql_session,
            after_time=fifth_transaction.time,
            until_time=second_transaction.time,
        )


def test_transaction_log_after_until_datetime_combined(sql_session: Session) -> None:
    user, user2, product, product2 = insert_test_data(sql_session)
    transactions = insert_default_test_transactions(sql_session, user, user2, product, product2)

    second_transaction = transactions[1]
    fifth_transaction = transactions[4]

    assert (
        len(
            transaction_log(
                sql_session,
                after_time=second_transaction.time,
                until_time=fifth_transaction.time,
            ),
        )
        == 4
    )


def test_transaction_log_after_until_transaction_illegal_order(sql_session: Session) -> None:
    user, user2, product, product2 = insert_test_data(sql_session)
    transactions = insert_default_test_transactions(sql_session, user, user2, product, product2)

    second_transaction = transactions[1]
    fifth_transaction = transactions[4]

    with pytest.raises(ValueError):
        transaction_log(
            sql_session,
            after_transaction=fifth_transaction,
            until_transaction=second_transaction,
        )


def test_transaction_log_after_until_transaction_combined(sql_session: Session) -> None:
    user, user2, product, product2 = insert_test_data(sql_session)
    transactions = insert_default_test_transactions(sql_session, user, user2, product, product2)

    second_transaction = transactions[1]
    fifth_transaction = transactions[4]

    assert (
        len(
            transaction_log(
                sql_session,
                after_transaction=second_transaction,
                until_transaction=fifth_transaction,
            ),
        )
        == 4
    )


def test_transaction_log_after_date_until_transaction(sql_session: Session) -> None:
    user, user2, product, product2 = insert_test_data(sql_session)
    transactions = insert_default_test_transactions(sql_session, user, user2, product, product2)

    second_transaction = transactions[1]
    fifth_transaction = transactions[4]

    assert (
        len(
            transaction_log(
                sql_session,
                after_time=second_transaction.time,
                until_transaction=fifth_transaction,
            ),
        )
        == 4
    )


def test_transaction_log_after_transaction_until_date(sql_session: Session) -> None:
    user, user2, product, product2 = insert_test_data(sql_session)
    transactions = insert_default_test_transactions(sql_session, user, user2, product, product2)

    second_transaction = transactions[1]
    fifth_transaction = transactions[4]

    assert (
        len(
            transaction_log(
                sql_session,
                after_transaction=second_transaction,
                until_time=fifth_transaction.time,
            ),
        )
        == 4
    )


def test_transaction_log_limit(sql_session: Session) -> None:
    user, user2, product, product2 = insert_test_data(sql_session)
    transactions = insert_default_test_transactions(sql_session, user, user2, product, product2)

    assert len(transaction_log(sql_session, limit=3)) == 3
    assert len(transaction_log(sql_session, limit=len(transactions) + 3)) == len(transactions)


def test_transaction_log_filtered_by_transaction_type(sql_session: Session) -> None:
    user, user2, product, product2 = insert_test_data(sql_session)
    insert_default_test_transactions(sql_session, user, user2, product, product2)

    assert (
        len(
            transaction_log(
                sql_session,
                transaction_type=[TransactionType.ADJUST_BALANCE],
            ),
        )
        == 3
    )
    assert (
        len(
            transaction_log(
                sql_session,
                transaction_type=[TransactionType.ADD_PRODUCT],
            ),
        )
        == 2
    )
    assert (
        len(
            transaction_log(
                sql_session,
                transaction_type=[TransactionType.BUY_PRODUCT, TransactionType.ADD_PRODUCT],
            ),
        )
        == 3
    )


def test_transaction_log_filtered_by_transaction_type_negated(sql_session: Session) -> None:
    user, user2, product, product2 = insert_test_data(sql_session)
    transactions = insert_default_test_transactions(sql_session, user, user2, product, product2)

    assert (
        len(
            transaction_log(
                sql_session,
                transaction_type=[TransactionType.ADJUST_BALANCE],
                negate_transaction_type_filter=True,
            ),
        )
        == len(transactions) - 3
    )
    assert (
        len(
            transaction_log(
                sql_session,
                transaction_type=[TransactionType.ADD_PRODUCT],
                negate_transaction_type_filter=True,
            ),
        )
        == len(transactions) - 2
    )
    assert (
        len(
            transaction_log(
                sql_session,
                transaction_type=[TransactionType.BUY_PRODUCT, TransactionType.ADD_PRODUCT],
                negate_transaction_type_filter=True,
            ),
        )
        == len(transactions) - 3
    )


def test_transaction_log_combined_filter_user_datetime_transaction_type_limit(
    sql_session: Session,
) -> None:
    user, user2, product, product2 = insert_test_data(sql_session)
    transactions = insert_default_test_transactions(sql_session, user, user2, product, product2)

    second_transaction = transactions[1]
    sixth_transaction = transactions[5]

    result = transaction_log(
        sql_session,
        user=user,
        after_time=second_transaction.time,
        until_time=sixth_transaction.time,
        transaction_type=[TransactionType.ADJUST_BALANCE, TransactionType.ADD_PRODUCT],
        limit=2,
    )

    assert len(result) == 2


def test_transaction_log_combined_filter_user_transaction_transaction_type_limit(
    sql_session: Session,
) -> None:
    user, user2, product, product2 = insert_test_data(sql_session)
    transactions = insert_default_test_transactions(sql_session, user, user2, product, product2)

    second_transaction = transactions[1]
    sixth_transaction = transactions[5]

    result = transaction_log(
        sql_session,
        user=user,
        after_transaction=second_transaction,
        until_transaction=sixth_transaction,
        transaction_type=[TransactionType.ADJUST_BALANCE, TransactionType.ADD_PRODUCT],
        limit=2,
    )

    assert len(result) == 2


def test_transaction_log_combined_filter_product_datetime_transaction_type_limit(
    sql_session: Session,
) -> None:
    user, user2, product, product2 = insert_test_data(sql_session)
    transactions = insert_default_test_transactions(sql_session, user, user2, product, product2)

    second_transaction = transactions[1]
    sixth_transaction = transactions[5]

    result = transaction_log(
        sql_session,
        product=product2,
        after_time=second_transaction.time,
        until_time=sixth_transaction.time,
        transaction_type=[TransactionType.BUY_PRODUCT, TransactionType.ADD_PRODUCT],
        limit=2,
    )

    assert len(result) == 2


def test_transaction_log_combined_filter_product_transaction_transaction_type_limit(
    sql_session: Session,
) -> None:
    user, user2, product, product2 = insert_test_data(sql_session)
    transactions = insert_default_test_transactions(sql_session, user, user2, product, product2)

    second_transaction = transactions[1]
    sixth_transaction = transactions[5]

    result = transaction_log(
        sql_session,
        product=product2,
        after_transaction=second_transaction,
        until_transaction=sixth_transaction,
        transaction_type=[TransactionType.BUY_PRODUCT, TransactionType.ADD_PRODUCT],
        limit=2,
    )

    assert len(result) == 2


# NOTE: see the corresponding TODO's above the function definition


@pytest.mark.skip(reason="Not yet implemented")
def test_transaction_log_filtered_by_user_joint_transactions(sql_session: Session) -> None: ...


@pytest.mark.skip(reason="Not yet implemented")
def test_transaction_log_filtered_by_user_throw_away_transactions(sql_session: Session) -> None: ...

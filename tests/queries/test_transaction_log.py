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
            time=datetime(2023, 10, 1, 10, 0, 0),
            amount=100,
            user_id=user1.id,
        ),
        Transaction.adjust_balance(
            time=datetime(2023, 10, 1, 10, 0, 1),
            amount=50,
            user_id=user2.id,
        ),
        Transaction.adjust_balance(
            time=datetime(2023, 10, 1, 10, 0, 2),
            amount=-50,
            user_id=user1.id,
        ),
        Transaction.add_product(
            time=datetime(2023, 10, 1, 12, 0, 0),
            amount=27 * 2,
            per_product=27,
            product_count=2,
            user_id=user1.id,
            product_id=product1.id,
        ),
        Transaction.buy_product(
            time=datetime(2023, 10, 1, 12, 0, 1),
            product_count=1,
            user_id=user2.id,
            product_id=product2.id,
        ),
        Transaction.add_product(
            time=datetime(2023, 10, 1, 12, 0, 2),
            amount=15 * 1,
            per_product=15,
            product_count=1,
            user_id=user2.id,
            product_id=product2.id,
        ),
        Transaction.transfer(
            time=datetime(2023, 10, 1, 14, 0, 0),
            amount=30,
            user_id=user1.id,
            transfer_user_id=user2.id,
        ),
    ]

    sql_session.add_all(transactions)
    sql_session.commit()

    return transactions


def test_user_transactions_no_transactions(sql_session: Session):
    insert_test_data(sql_session)

    transactions = transaction_log(sql_session)

    assert len(transactions) == 0


def test_transaction_log_filtered_by_user(sql_session: Session):
    user, user2, product, product2 = insert_test_data(sql_session)
    insert_default_test_transactions(sql_session, user, user2, product, product2)

    assert len(transaction_log(sql_session, user=user)) == 4
    assert len(transaction_log(sql_session, user=user2)) == 3


def test_transaction_log_filtered_by_product(sql_session: Session):
    user, user2, product, product2 = insert_test_data(sql_session)
    insert_default_test_transactions(sql_session, user, user2, product, product2)

    assert len(transaction_log(sql_session, product=product)) == 1
    assert len(transaction_log(sql_session, product=product2)) == 2


def test_transaction_log_after_datetime(sql_session: Session):
    user, user2, product, product2 = insert_test_data(sql_session)
    transactions = insert_default_test_transactions(sql_session, user, user2, product, product2)

    assert (
        len(
            transaction_log(
                sql_session,
                after_time=transactions[2].time,
            )
        )
        == len(transactions) - 2
    )


def test_transaction_log_after_datetime_no_transactions(sql_session: Session):
    user, user2, product, product2 = insert_test_data(sql_session)
    transactions = insert_default_test_transactions(sql_session, user, user2, product, product2)
    assert (
        len(
            transaction_log(
                sql_session,
                after_time=transactions[-1].time + timedelta(seconds=1),
            )
        )
        == 0
    )


def test_transaction_log_after_datetime_exclusive(sql_session: Session):
    user, user2, product, product2 = insert_test_data(sql_session)
    transactions = insert_default_test_transactions(sql_session, user, user2, product, product2)

    assert (
        len(
            transaction_log(
                sql_session,
                after_time=transactions[2].time,
                exclusive_after=True,
            )
        )
        == len(transactions) - 3
    )


def test_transaction_log_after_transaction_id(sql_session: Session):
    user, user2, product, product2 = insert_test_data(sql_session)
    transactions = insert_default_test_transactions(sql_session, user, user2, product, product2)

    first_transaction = transactions[0]

    assert len(
        transaction_log(
            sql_session,
            after_transaction_id=first_transaction.id,
        )
    ) == len(transactions)


def test_transaction_log_after_transaction_id_one_transaction(sql_session: Session):
    user, user2, product, product2 = insert_test_data(sql_session)
    transactions = insert_default_test_transactions(sql_session, user, user2, product, product2)

    last_transaction = transactions[-1]

    assert (
        len(
            transaction_log(
                sql_session,
                after_transaction_id=last_transaction.id,
            )
        )
        == 1
    )


def test_transaction_log_after_transaction_id_exclusive(sql_session: Session):
    user, user2, product, product2 = insert_test_data(sql_session)
    transactions = insert_default_test_transactions(sql_session, user, user2, product, product2)

    third_transaction = transactions[2]

    assert (
        len(
            transaction_log(
                sql_session,
                after_transaction_id=third_transaction.id,
                exclusive_after=True,
            )
        )
        == len(transactions) - 3
    )


def test_transaction_log_before_datetime(sql_session: Session):
    user, user2, product, product2 = insert_test_data(sql_session)
    transactions = insert_default_test_transactions(sql_session, user, user2, product, product2)

    assert (
        len(
            transaction_log(
                sql_session,
                before_time=transactions[-3].time,
            )
        )
        == len(transactions) - 2
    )


def test_transaction_log_before_datetime_no_transactions(sql_session: Session):
    user, user2, product, product2 = insert_test_data(sql_session)
    transactions = insert_default_test_transactions(sql_session, user, user2, product, product2)

    assert (
        len(
            transaction_log(
                sql_session,
                before_time=transactions[0].time - timedelta(seconds=1),
            )
        )
        == 0
    )


def test_transaction_log_before_datetime_exclusive(sql_session: Session):
    user, user2, product, product2 = insert_test_data(sql_session)
    transactions = insert_default_test_transactions(sql_session, user, user2, product, product2)

    assert (
        len(
            transaction_log(
                sql_session,
                before_time=transactions[-3].time,
                exclusive_before=True,
            )
        )
        == len(transactions) - 3
    )


def test_transaction_log_before_transaction_id(sql_session: Session):
    user, user2, product, product2 = insert_test_data(sql_session)
    transactions = insert_default_test_transactions(sql_session, user, user2, product, product2)

    last_transaction = transactions[-3]

    assert (
        len(
            transaction_log(
                sql_session,
                before_transaction_id=last_transaction.id,
            )
        )
        == len(transactions) - 2
    )


def test_transaction_log_before_transaction_id_one_transaction(sql_session: Session):
    user, user2, product, product2 = insert_test_data(sql_session)
    transactions = insert_default_test_transactions(sql_session, user, user2, product, product2)

    first_transaction = transactions[0]

    assert (
        len(
            transaction_log(
                sql_session,
                before_transaction_id=first_transaction.id,
            )
        )
        == 1
    )


def test_transaction_log_before_transaction_id_exclusive(sql_session: Session):
    user, user2, product, product2 = insert_test_data(sql_session)
    transactions = insert_default_test_transactions(sql_session, user, user2, product, product2)

    last_transaction = transactions[-3]

    assert (
        len(
            transaction_log(
                sql_session,
                before_transaction_id=last_transaction.id,
                exclusive_before=True,
            )
        )
        == len(transactions) - 3
    )


def test_transaction_log_before_after_datetime_combined(sql_session: Session):
    user, user2, product, product2 = insert_test_data(sql_session)
    transactions = insert_default_test_transactions(sql_session, user, user2, product, product2)

    second_transaction = transactions[1]
    fifth_transaction = transactions[4]

    assert (
        len(
            transaction_log(
                sql_session,
                after_time=second_transaction.time,
                before_time=fifth_transaction.time,
            )
        )
        == 4
    )


def test_transaction_log_before_after_transaction_id_combined(sql_session: Session):
    user, user2, product, product2 = insert_test_data(sql_session)
    transactions = insert_default_test_transactions(sql_session, user, user2, product, product2)

    second_transaction = transactions[1]
    fifth_transaction = transactions[4]

    assert (
        len(
            transaction_log(
                sql_session,
                after_transaction_id=second_transaction.id,
                before_transaction_id=fifth_transaction.id,
            )
        )
        == 4
    )


def test_transaction_log_before_date_after_transaction_id(sql_session: Session):
    user, user2, product, product2 = insert_test_data(sql_session)
    transactions = insert_default_test_transactions(sql_session, user, user2, product, product2)

    second_transaction = transactions[1]
    fifth_transaction = transactions[4]

    assert (
        len(
            transaction_log(
                sql_session,
                before_time=fifth_transaction.time,
                after_transaction_id=second_transaction.id,
            )
        )
        == 4
    )


def test_transaction_log_before_transaction_id_after_date(sql_session: Session):
    user, user2, product, product2 = insert_test_data(sql_session)
    transactions = insert_default_test_transactions(sql_session, user, user2, product, product2)

    second_transaction = transactions[1]
    fifth_transaction = transactions[4]

    assert (
        len(
            transaction_log(
                sql_session,
                before_transaction_id=fifth_transaction.id,
                after_time=second_transaction.time,
            )
        )
        == 4
    )


def test_transaction_log_after_product_and_user_not_allowed(sql_session: Session):
    user, user2, product, product2 = insert_test_data(sql_session)
    insert_default_test_transactions(sql_session, user, user2, product, product2)

    with pytest.raises(ValueError):
        transaction_log(
            sql_session,
            user=user,
            product=product,
            after_time=datetime(2023, 10, 1, 11, 0, 0),
        )


def test_transaction_log_after_datetime_and_transaction_id_not_allowed(sql_session: Session):
    user, user2, product, product2 = insert_test_data(sql_session)
    insert_default_test_transactions(sql_session, user, user2, product, product2)

    with pytest.raises(ValueError):
        transaction_log(
            sql_session,
            user=user,
            after_time=datetime(2023, 10, 1, 11, 0, 0),
            after_transaction_id=1,
        )


def test_transaction_log_limit(sql_session: Session):
    user, user2, product, product2 = insert_test_data(sql_session)
    transactions = insert_default_test_transactions(sql_session, user, user2, product, product2)

    assert len(transaction_log(sql_session, limit=3)) == 3
    assert len(transaction_log(sql_session, limit=len(transactions) + 3)) == len(transactions)


def test_transaction_log_filtered_by_transaction_type(sql_session: Session):
    user, user2, product, product2 = insert_test_data(sql_session)
    insert_default_test_transactions(sql_session, user, user2, product, product2)

    assert (
        len(
            transaction_log(
                sql_session,
                transaction_type=[TransactionType.ADJUST_BALANCE],
            )
        )
        == 3
    )
    assert (
        len(
            transaction_log(
                sql_session,
                transaction_type=[TransactionType.ADD_PRODUCT],
            )
        )
        == 2
    )
    assert (
        len(
            transaction_log(
                sql_session,
                transaction_type=[TransactionType.BUY_PRODUCT, TransactionType.ADD_PRODUCT],
            )
        )
        == 3
    )


def test_transaction_log_filtered_by_transaction_type_negated(sql_session: Session):
    user, user2, product, product2 = insert_test_data(sql_session)
    transactions = insert_default_test_transactions(sql_session, user, user2, product, product2)

    assert (
        len(
            transaction_log(
                sql_session,
                transaction_type=[TransactionType.ADJUST_BALANCE],
                negate_transaction_type_filter=True,
            )
        )
        == len(transactions) - 3
    )
    assert (
        len(
            transaction_log(
                sql_session,
                transaction_type=[TransactionType.ADD_PRODUCT],
                negate_transaction_type_filter=True,
            )
        )
        == len(transactions) - 2
    )
    assert (
        len(
            transaction_log(
                sql_session,
                transaction_type=[TransactionType.BUY_PRODUCT, TransactionType.ADD_PRODUCT],
                negate_transaction_type_filter=True,
            )
        )
        == len(transactions) - 3
    )


def test_transaction_log_combined_filter_user_datetime_transaction_type_limit(
    sql_session: Session,
):
    user, user2, product, product2 = insert_test_data(sql_session)
    transactions = insert_default_test_transactions(sql_session, user, user2, product, product2)

    second_transaction = transactions[1]
    sixth_transaction = transactions[5]

    result = transaction_log(
        sql_session,
        user=user,
        after_time=second_transaction.time,
        before_time=sixth_transaction.time,
        transaction_type=[TransactionType.ADJUST_BALANCE, TransactionType.ADD_PRODUCT],
        limit=2,
    )

    assert len(result) == 2


def test_transaction_log_combined_filter_user_transaction_id_transaction_type_limit(
    sql_session: Session,
):
    user, user2, product, product2 = insert_test_data(sql_session)
    transactions = insert_default_test_transactions(sql_session, user, user2, product, product2)

    second_transaction = transactions[1]
    sixth_transaction = transactions[5]

    result = transaction_log(
        sql_session,
        user=user,
        after_transaction_id=second_transaction.id,
        before_transaction_id=sixth_transaction.id,
        transaction_type=[TransactionType.ADJUST_BALANCE, TransactionType.ADD_PRODUCT],
        limit=2,
    )

    assert len(result) == 2


def test_transaction_log_combined_filter_product_datetime_transaction_type_limit(
    sql_session: Session,
):
    user, user2, product, product2 = insert_test_data(sql_session)
    transactions = insert_default_test_transactions(sql_session, user, user2, product, product2)

    second_transaction = transactions[1]
    sixth_transaction = transactions[5]

    result = transaction_log(
        sql_session,
        product=product2,
        after_time=second_transaction.time,
        before_time=sixth_transaction.time,
        transaction_type=[TransactionType.BUY_PRODUCT, TransactionType.ADD_PRODUCT],
        limit=2,
    )

    assert len(result) == 2


def test_transaction_log_combined_filter_product_transaction_id_transaction_type_limit(
    sql_session: Session,
):
    user, user2, product, product2 = insert_test_data(sql_session)
    transactions = insert_default_test_transactions(sql_session, user, user2, product, product2)

    second_transaction = transactions[1]
    sixth_transaction = transactions[5]

    result = transaction_log(
        sql_session,
        product=product2,
        after_transaction_id=second_transaction.id,
        before_transaction_id=sixth_transaction.id,
        transaction_type=[TransactionType.BUY_PRODUCT, TransactionType.ADD_PRODUCT],
        limit=2,
    )

    assert len(result) == 2


def test_transaction_log_filtered_by_user_joint_transactions(sql_session: Session): ...

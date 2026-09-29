from datetime import datetime

import pytest
from sqlalchemy.orm import Session

from dibbler.models import Product, TransactionLog, TransactionLogProduct, TransactionLogUser, User
from dibbler.models.enums import TransactionLogEntryType


def _make_entry(
    sql_session: Session,
    entry_type: TransactionLogEntryType,
    user_count: int,
    product_count: int,
    user_amount: int | None = 1,
) -> TransactionLog:
    users = [User(f"user{i}", None) for i in range(user_count)]
    products = [Product(f"{i:013d}", f"product{i}", price=10) for i in range(product_count)]
    sql_session.add_all([*users, *products])
    sql_session.flush()

    entry = TransactionLog(
        type=entry_type,
        time=datetime(2024, 1, 1),
        users={TransactionLogUser(user=user, amount=user_amount) for user in users},
        products={
            TransactionLogProduct(
                product=product,
                amount=1,
                price_at_time=product.price,
            )
            for product in products
        },
    )

    sql_session.add_all(entry.users)
    sql_session.add_all(entry.products)
    sql_session.add(entry)

    # Explicitly don't flush, so we can test invalid entries down below

    return entry


VALID_ENTRIES = [
    # (type, user count, product count, user amount)
    (TransactionLogEntryType.BUY_PRODUCT, 1, 1, 5),
    (TransactionLogEntryType.BUY_PRODUCT, 3, 2, 5),
    (TransactionLogEntryType.ADD_PRODUCT, 1, 1, 5),
    (TransactionLogEntryType.ADD_PRODUCT, 2, 3, 5),
    (TransactionLogEntryType.ADD_PRODUCT, 1, 1, 0),
    (TransactionLogEntryType.ADJUST_STOCK, 1, 1, None),
    (TransactionLogEntryType.TRANSFER, 2, 0, 5),
    (TransactionLogEntryType.ADJUST_BALANCE, 1, 0, 5),
    (TransactionLogEntryType.ADJUST_BALANCE, 1, 0, -5),
]


@pytest.mark.parametrize(
    ("entry_type", "user_count", "product_count", "user_amount"),
    VALID_ENTRIES,
)
def test_valid_entry_is_accepted(
    sql_session: Session,
    entry_type: TransactionLogEntryType,
    user_count: int,
    product_count: int,
    user_amount: int | None,
) -> None:
    entry = _make_entry(sql_session, entry_type, user_count, product_count, user_amount)

    sql_session.flush()

    assert entry.id is not None


INVALID_USER_PRODUCT_COUNTS = [
    (TransactionLogEntryType.BUY_PRODUCT, 0, 0),
    (TransactionLogEntryType.BUY_PRODUCT, 0, 1),
    (TransactionLogEntryType.BUY_PRODUCT, 1, 0),
    (TransactionLogEntryType.ADD_PRODUCT, 0, 0),
    (TransactionLogEntryType.ADD_PRODUCT, 0, 1),
    (TransactionLogEntryType.ADD_PRODUCT, 1, 0),
    (TransactionLogEntryType.ADJUST_STOCK, 0, 0),
    (TransactionLogEntryType.ADJUST_STOCK, 0, 1),
    (TransactionLogEntryType.ADJUST_STOCK, 1, 0),
    (TransactionLogEntryType.ADJUST_STOCK, 1, 2),
    (TransactionLogEntryType.ADJUST_STOCK, 2, 1),
    (TransactionLogEntryType.TRANSFER, 0, 0),
    (TransactionLogEntryType.TRANSFER, 1, 0),
    (TransactionLogEntryType.TRANSFER, 3, 0),
    (TransactionLogEntryType.TRANSFER, 2, 1),
    (TransactionLogEntryType.ADJUST_BALANCE, 0, 0),
    (TransactionLogEntryType.ADJUST_BALANCE, 2, 0),
    (TransactionLogEntryType.ADJUST_BALANCE, 1, 1),
]


@pytest.mark.parametrize(("entry_type", "user_count", "product_count"), INVALID_USER_PRODUCT_COUNTS)
def test_invalid_shape_is_rejected(
    sql_session: Session,
    entry_type: TransactionLogEntryType,
    user_count: int,
    product_count: int,
) -> None:
    _make_entry(sql_session, entry_type, user_count, product_count)

    with pytest.raises(ValueError, match=f"A {entry_type} log entry must have"):
        sql_session.flush()


# NOTE: these tests are referring to the amount of credits related to the user in the log,
#       not the amount of users.

INVALID_USER_AMOUNTS = [
    # (type, user count, product count, user amount)
    (TransactionLogEntryType.BUY_PRODUCT, 1, 1, None),
    (TransactionLogEntryType.BUY_PRODUCT, 1, 1, 0),
    (TransactionLogEntryType.ADD_PRODUCT, 1, 1, None),
    (TransactionLogEntryType.ADJUST_STOCK, 1, 1, 0),
    (TransactionLogEntryType.ADJUST_STOCK, 1, 1, 5),
    (TransactionLogEntryType.TRANSFER, 2, 0, None),
    (TransactionLogEntryType.TRANSFER, 2, 0, 0),
    (TransactionLogEntryType.ADJUST_BALANCE, 1, 0, None),
    (TransactionLogEntryType.ADJUST_BALANCE, 1, 0, 0),
]


@pytest.mark.parametrize(
    ("entry_type", "user_count", "product_count", "user_amount"),
    INVALID_USER_AMOUNTS,
)
def test_invalid_user_amount_is_rejected(
    sql_session: Session,
    entry_type: TransactionLogEntryType,
    user_count: int,
    product_count: int,
    user_amount: int | None,
) -> None:
    _make_entry(sql_session, entry_type, user_count, product_count, user_amount)

    with pytest.raises(ValueError, match=f"Every user in a {entry_type} log entry must have"):
        sql_session.flush()

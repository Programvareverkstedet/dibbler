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
) -> TransactionLog:
    users = [User(f"user{i}", None) for i in range(user_count)]
    products = [Product(f"{i:013d}", f"product{i}", price=10) for i in range(product_count)]
    sql_session.add_all([*users, *products])
    sql_session.flush()

    entry = TransactionLog(
        type=entry_type,
        time=datetime(2024, 1, 1),
        users={TransactionLogUser(user=user, amount=1) for user in users},
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


VALID_USER_PRODUCT_COUNTS = [
    (TransactionLogEntryType.BUY_PRODUCT, 1, 1),
    (TransactionLogEntryType.BUY_PRODUCT, 3, 2),

    (TransactionLogEntryType.ADD_PRODUCT, 1, 1),
    (TransactionLogEntryType.ADD_PRODUCT, 2, 3),

    (TransactionLogEntryType.ADJUST_STOCK, 0, 1),

    (TransactionLogEntryType.TRANSFER, 2, 0),

    (TransactionLogEntryType.ADJUST_BALANCE, 1, 0),
]


@pytest.mark.parametrize(("entry_type", "user_count", "product_count"), VALID_USER_PRODUCT_COUNTS)
def test_valid_shape_is_accepted(
    sql_session: Session,
    entry_type: TransactionLogEntryType,
    user_count: int,
    product_count: int,
) -> None:
    entry = _make_entry(sql_session, entry_type, user_count, product_count)

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
    (TransactionLogEntryType.ADJUST_STOCK, 0, 2),

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

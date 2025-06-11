from datetime import datetime
from pathlib import Path

from dibbler.db import Session
from dibbler.models import Product, Transaction, TransactionType, User

JSON_FILE = Path(__file__).parent.parent.parent / "mock_data.json"


# TODO: integrate this as a part of create-db, either asking interactively
#       whether to seed test data, or by using command line arguments for
#       automatating the answer.

def clear_db(sql_session):
    sql_session.query(Product).delete()
    sql_session.query(User).delete()
    sql_session.commit()


def main():
    # TODO: There is some leftover json data in the mock_data.json file.
    #       It should be dealt with before merging this PR, either by removing
    #       it or using it here.
    sql_session = Session()
    clear_db(sql_session)

    # Add users
    user1 = User("Test User 1")
    user2 = User("Test User 2")

    sql_session.add(user1)
    sql_session.add(user2)
    sql_session.commit()

    # Add products
    product1 = Product("1234567890123", "Test Product 1")
    product2 = Product("9876543210987", "Test Product 2")
    sql_session.add(product1)
    sql_session.add(product2)
    sql_session.commit()

    # Add transactions
    transactions = [
        Transaction(
            time=datetime(2023, 10, 1, 10, 0, 0),
            type_=TransactionType.ADJUST_BALANCE,
            amount=100,
            user_id=user1.id,
        ),
        Transaction(
            time=datetime(2023, 10, 1, 10, 0, 1),
            type_=TransactionType.ADJUST_BALANCE,
            amount=50,
            user_id=user2.id,
        ),
        Transaction(
            time=datetime(2023, 10, 1, 10, 0, 2),
            type_=TransactionType.ADJUST_BALANCE,
            amount=-50,
            user_id=user1.id,
        ),
        Transaction(
            time=datetime(2023, 10, 1, 12, 0, 0),
            type_=TransactionType.ADD_PRODUCT,
            amount=27 * 2,
            per_product=27,
            product_count=2,
            user_id=user1.id,
            product_id=product1.id,
        ),
        Transaction(
            time=datetime(2023, 10, 1, 12, 0, 1),
            type_=TransactionType.BUY_PRODUCT,
            amount=27,
            product_count=1,
            user_id=user2.id,
            product_id=product1.id,
        ),
    ]

    sql_session.add_all(transactions)
    sql_session.commit()

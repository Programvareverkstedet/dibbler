import math
from datetime import datetime
from pprint import pprint

from sqlalchemy.orm import Session

from dibbler.models import Product, Transaction, User
from dibbler.queries.product_price import product_price, product_price_log

# TODO: see if we can use pytest_runtest_makereport to print the "product_price_log"s
#       only on failures instead of inlining it in every test function


def insert_test_data(sql_session: Session) -> tuple[User, Product]:
    user = User("Test User")
    product = Product("1234567890123", "Test Product")

    sql_session.add(user)
    sql_session.add(product)
    sql_session.commit()

    return user, product


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
            time=datetime(2023, 10, 1, 12, 0, 0),
            amount=27 * 2 - 1,
            per_product=27,
            product_count=2,
            user_id=user.id,
            product_id=product.id,
        ),
        Transaction.buy_product(
            time=datetime(2023, 10, 1, 12, 0, 1),
            product_count=2,
            user_id=user.id,
            product_id=product.id,
        ),
    ]

    sql_session.add_all(transactions)
    sql_session.commit()

    pprint(product_price_log(sql_session, product))

    assert product_price(sql_session, product) == 27


def test_product_price_interest(sql_session: Session) -> None:
    user, product = insert_test_data(sql_session)

    transactions = [
        Transaction.adjust_interest(
            time=datetime(2023, 10, 1, 12, 0, 0),
            interest_rate_percent=110,
            user_id=user.id,
        ),
        Transaction.add_product(
            time=datetime(2023, 10, 1, 12, 0, 1),
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

    product_price_ = product_price(sql_session, product)
    product_price_interest = product_price(sql_session, product, include_interest=True)

    assert product_price_ == 27
    assert product_price_interest == math.ceil(27 * 1.1)


def test_product_price_changing_interest(sql_session: Session) -> None:
    user, product = insert_test_data(sql_session)

    transactions = [
        Transaction.adjust_interest(
            time=datetime(2023, 10, 1, 12, 0, 0),
            interest_rate_percent=110,
            user_id=user.id,
        ),
        Transaction.add_product(
            time=datetime(2023, 10, 1, 12, 0, 1),
            amount=27 * 2 - 1,
            per_product=27,
            product_count=2,
            user_id=user.id,
            product_id=product.id,
        ),
        Transaction.adjust_interest(
            time=datetime(2023, 10, 1, 12, 0, 2),
            interest_rate_percent=120,
            user_id=user.id,
        ),
    ]

    sql_session.add_all(transactions)
    sql_session.commit()

    pprint(product_price_log(sql_session, product))

    product_price_interest = product_price(sql_session, product, include_interest=True)
    assert product_price_interest == math.ceil(27 * 1.2)


def test_product_price_old_transaction(sql_session: Session) -> None:
    user, product = insert_test_data(sql_session)

    transactions = [
        Transaction.add_product(
            time=datetime(2023, 10, 1, 12, 0, 1),
            amount=27 * 2,
            per_product=27,
            product_count=2,
            user_id=user.id,
            product_id=product.id,
        ),
        # Price should be 27
        Transaction.add_product(
            time=datetime(2023, 10, 1, 12, 0, 2),
            amount=38 * 3,
            per_product=38,
            product_count=3,
            user_id=user.id,
            product_id=product.id,
        ),
        # price should be averaged upwards
    ]

    sql_session.add_all(transactions)
    sql_session.commit()

    until_transaction = transactions[0]

    pprint(
        product_price_log(
            sql_session,
            product,
            until=until_transaction,
        )
    )

    product_price_ = product_price(
        sql_session,
        product,
        until=until_transaction,
    )
    assert product_price_ == 27


# Price goes up and gets rounded up to the next integer
def test_product_price_round_up_from_below(sql_session: Session) -> None:
    user, product = insert_test_data(sql_session)

    transactions = [
        Transaction.add_product(
            time=datetime(2023, 10, 1, 12, 0, 1),
            amount=27 * 2,
            per_product=27,
            product_count=2,
            user_id=user.id,
            product_id=product.id,
        ),
        # Price should be 27
        Transaction.add_product(
            time=datetime(2023, 10, 1, 12, 0, 2),
            amount=38 * 3,
            per_product=38,
            product_count=3,
            user_id=user.id,
            product_id=product.id,
        ),
        # price should be averaged upwards
    ]

    sql_session.add_all(transactions)
    sql_session.commit()

    pprint(product_price_log(sql_session, product))

    product_price_ = product_price(sql_session, product)
    assert product_price_ == math.ceil((27 * 2 + 38 * 3) / (2 + 3))


# Price goes down and gets rounded up to the next integer
def test_product_price_round_up_from_above(sql_session: Session) -> None:
    user, product = insert_test_data(sql_session)

    transactions = [
        Transaction.add_product(
            time=datetime(2023, 10, 1, 12, 0, 1),
            amount=27 * 2,
            per_product=27,
            product_count=2,
            user_id=user.id,
            product_id=product.id,
        ),
        # Price should be 27
        Transaction.add_product(
            time=datetime(2023, 10, 1, 12, 0, 2),
            amount=20 * 3,
            per_product=20,
            product_count=3,
            user_id=user.id,
            product_id=product.id,
        ),
        # price should be averaged downwards
    ]

    sql_session.add_all(transactions)
    sql_session.commit()

    pprint(product_price_log(sql_session, product))

    product_price_ = product_price(sql_session, product)
    assert product_price_ == math.ceil((27 * 2 + 20 * 3) / (2 + 3))


def test_product_price_with_negative_stock_single_addition(sql_session: Session) -> None:
    user, product = insert_test_data(sql_session)

    transactions = [
        Transaction.add_product(
            time=datetime(2023, 10, 1, 13, 0, 0),
            amount=1,
            per_product=10,
            product_count=1,
            user_id=user.id,
            product_id=product.id,
        ),
        Transaction.buy_product(
            time=datetime(2023, 10, 1, 13, 0, 1),
            product_count=10,
            user_id=user.id,
            product_id=product.id,
        ),
        Transaction.add_product(
            time=datetime(2023, 10, 1, 13, 0, 2),
            amount=22,
            per_product=22,
            product_count=1,
            user_id=user.id,
            product_id=product.id,
        ),
    ]

    sql_session.add_all(transactions)
    sql_session.commit()

    pprint(product_price_log(sql_session, product))

    # Stock went subzero, price should be the last added product price
    product1_price = product_price(sql_session, product)
    assert product1_price == 22


# TODO: what happens when stock is still negative and yet new products are added?
def test_product_price_with_negative_stock_multiple_additions(sql_session: Session) -> None:
    user, product = insert_test_data(sql_session)

    transactions = [
        Transaction.add_product(
            time=datetime(2023, 10, 1, 13, 0, 0),
            amount=1,
            per_product=10,
            product_count=1,
            user_id=user.id,
            product_id=product.id,
        ),
        Transaction.buy_product(
            time=datetime(2023, 10, 1, 13, 0, 1),
            product_count=10,
            user_id=user.id,
            product_id=product.id,
        ),
        Transaction.add_product(
            time=datetime(2023, 10, 1, 13, 0, 2),
            amount=22,
            per_product=22,
            product_count=1,
            user_id=user.id,
            product_id=product.id,
        ),
        Transaction.add_product(
            time=datetime(2023, 10, 1, 13, 0, 3),
            amount=29,
            per_product=29,
            product_count=2,
            user_id=user.id,
            product_id=product.id,
        ),
    ]

    sql_session.add_all(transactions)
    sql_session.commit()

    pprint(product_price_log(sql_session, product))

    # Stock went subzero, price should be the ceiled average of the last added products
    product1_price = product_price(sql_session, product)
    assert product1_price == math.ceil((22 + 29 * 2) / (1 + 2))

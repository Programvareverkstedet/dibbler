from sqlalchemy.orm import Session

from dibbler.models import Product, User
from dibbler.models.Transaction import Transaction
from dibbler.queries import product_owners


def insert_test_data(sql_session: Session) -> tuple[Product, User]:
    user = User("testuser")
    product = Product("1234567890123", "Test Product")

    sql_session.add(user)
    sql_session.add(product)

    sql_session.commit()

    return product, user


def test_product_owners_no_transactions(sql_session: Session) -> None:
    product, _ = insert_test_data(sql_session)

    owners = product_owners(sql_session, product)

    assert owners == []


def test_product_owners_add_products(sql_session: Session) -> None:
    product, user = insert_test_data(sql_session)

    transactions = [
        Transaction.add_product(
            user_id=user.id,
            product_id=product.id,
            amount=30,
            per_product=10,
            product_count=3,
        )
    ]
    sql_session.add_all(transactions)
    sql_session.commit()

    owners = product_owners(sql_session, product)

    assert owners == [user, user, user]


def test_product_owners_add_and_buy_products(sql_session: Session) -> None:
    product, user = insert_test_data(sql_session)
    transactions = [
        Transaction.add_product(
            user_id=user.id,
            product_id=product.id,
            amount=30,
            per_product=10,
            product_count=3,
        ),
        Transaction.buy_product(
            user_id=user.id,
            product_id=product.id,
            product_count=1,
        ),
    ]

    sql_session.add_all(transactions)
    sql_session.commit()

    owners = product_owners(sql_session, product)
    assert owners == [user, user]


def test_product_owners_add_and_throw_products(sql_session: Session) -> None:
    product, user = insert_test_data(sql_session)
    transactions = [
        Transaction.add_product(
            user_id=user.id,
            product_id=product.id,
            amount=40,
            per_product=10,
            product_count=4,
        ),
        Transaction.throw_product(
            user_id=user.id,
            product_id=product.id,
            product_count=2,
        ),
    ]

    sql_session.add_all(transactions)
    sql_session.commit()

    owners = product_owners(sql_session, product)
    assert owners == [user, user]


def test_product_owners_multiple_users(sql_session: Session) -> None:
    product, user1 = insert_test_data(sql_session)
    user2 = User("testuser2")
    sql_session.add(user2)
    sql_session.commit()
    transactions = [
        Transaction.add_product(
            user_id=user1.id,
            product_id=product.id,
            amount=20,
            per_product=10,
            product_count=2,
        ),
        Transaction.add_product(
            user_id=user2.id,
            product_id=product.id,
            amount=30,
            per_product=10,
            product_count=3,
        ),
    ]

    sql_session.add_all(transactions)
    sql_session.commit()

    owners = product_owners(sql_session, product)
    assert owners == [user2, user2, user2, user1, user1]


def test_product_owners_adjust_stock_down(sql_session: Session) -> None:
    product, user = insert_test_data(sql_session)

    transactions = [
        Transaction.add_product(
            user_id=user.id,
            product_id=product.id,
            amount=50,
            per_product=10,
            product_count=5,
        ),
        Transaction.adjust_stock(
            user_id=user.id,
            product_id=product.id,
            product_count=-2,
        ),
    ]
    sql_session.add_all(transactions)
    sql_session.commit()

    owners = product_owners(sql_session, product)

    assert owners == [user, user, user]


def test_product_owners_adjust_stock_up(sql_session: Session) -> None:
    product, user = insert_test_data(sql_session)

    transactions = [
        Transaction.add_product(
            user_id=user.id,
            product_id=product.id,
            amount=20,
            per_product=10,
            product_count=2,
        ),
        Transaction.adjust_stock(
            user_id=user.id,
            product_id=product.id,
            product_count=3,
        ),
    ]
    sql_session.add_all(transactions)
    sql_session.commit()

    owners = product_owners(sql_session, product)

    assert owners == [user, user, None, None, None]


def test_product_owners_negative_stock(sql_session: Session) -> None:
    product, user = insert_test_data(sql_session)

    transactions = [
        Transaction.add_product(
            user_id=user.id,
            product_id=product.id,
            amount=10,
            per_product=10,
            product_count=1,
        ),
        Transaction.buy_product(
            user_id=user.id,
            product_id=product.id,
            product_count=2,
        ),
    ]
    sql_session.add_all(transactions)
    sql_session.commit()

    owners = product_owners(sql_session, product)

    assert owners == []

def test_product_owners_add_products_from_negative_stock(sql_session: Session) -> None:
    product, user = insert_test_data(sql_session)

    transactions = [
        Transaction.buy_product(
            user_id=user.id,
            product_id=product.id,
            product_count=2,
        ),
        Transaction.add_product(
            user_id=user.id,
            product_id=product.id,
            amount=30,
            per_product=10,
            product_count=3,
        ),
    ]
    sql_session.add_all(transactions)
    sql_session.commit()

    owners = product_owners(sql_session, product)

    assert owners == [user]

def test_product_owners_interleaved_users(sql_session: Session) -> None:
    product, user1 = insert_test_data(sql_session)
    user2 = User("testuser2")
    sql_session.add(user2)
    sql_session.commit()

    transactions = [
        Transaction.add_product(
            user_id=user1.id,
            product_id=product.id,
            amount=20,
            per_product=10,
            product_count=2,
        ),
        Transaction.add_product(
            user_id=user2.id,
            product_id=product.id,
            amount=30,
            per_product=10,
            product_count=3,
        ),
        Transaction.buy_product(
            user_id=user1.id,
            product_id=product.id,
            product_count=1,
        ),
        Transaction.add_product(
            user_id=user1.id,
            product_id=product.id,
            amount=10,
            per_product=10,
            product_count=1,
        ),
    ]
    sql_session.add_all(transactions)
    sql_session.commit()

    owners = product_owners(sql_session, product)
    assert owners == [user1, user2, user2, user1, user1]

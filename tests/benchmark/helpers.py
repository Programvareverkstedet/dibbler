import random
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from dibbler.models import Product, Transaction, TransactionType, User
from dibbler.queries import joint_buy_product
from tests.benchmark.benchmark_settings import TRANSACTION_GENERATOR_EXCEPTION_LIMIT


def insert_users_and_products(
    sql_session: Session,
    user_count: int = 10,
    product_count: int = 10,
) -> tuple[list[User], list[Product]]:
    users = []
    for i in range(user_count):
        user = User(f"User{i + 1}")
        sql_session.add(user)
        users.append(user)
    sql_session.commit()

    products = []
    for i in range(product_count):
        barcode = str(1000000000000 + i)
        product = Product(barcode, f"Product{i + 1}")
        sql_session.add(product)
        products.append(product)
    sql_session.commit()

    return users, products


def generate_random_transactions(
    sql_session: Session,
    n: int,
    seed: int = 42,
    transaction_type_filter: list[TransactionType] | None = None,
    distribution: dict[TransactionType, float] | None = None,
    cache_every_n: int | None = None,
) -> list[Transaction]:
    random.seed(seed)

    if transaction_type_filter is None:
        transaction_type_filter = list(TransactionType)

    if TransactionType.JOINT_BUY_PRODUCT in transaction_type_filter:
        transaction_type_filter.remove(TransactionType.JOINT_BUY_PRODUCT)

    # TODO: implement me
    if TransactionType.THROW_PRODUCT in transaction_type_filter:
        transaction_type_filter.remove(TransactionType.THROW_PRODUCT)

    if distribution is None:
        distribution = {t: 1 / len(transaction_type_filter) for t in transaction_type_filter}
    transaction_types = list(distribution.keys())
    weights = list(distribution.values())
    transactions: list[Transaction] = []
    last_time = datetime(2023, 1, 1, 0, 0, 0)
    for _ in range(n):
        transaction_type = random.choices(transaction_types, weights=weights, k=1)[0]
        generator = RANDOM_GENERATORS[transaction_type]
        transaction_or_transactions = generator(sql_session, last_time)
        if isinstance(transaction_or_transactions, list):
            transactions.extend(transaction_or_transactions)
            last_time = max(t.time for t in transaction_or_transactions)
        else:
            transactions.append(transaction_or_transactions)
            last_time = transaction_or_transactions.time
    return transactions


def random_add_product_transaction(sql_session: Session, last_time: datetime) -> Transaction:
    i = 0
    while True:
        i += 1
        user = random.choice(sql_session.query(User).all())
        product = random.choice(sql_session.query(Product).all())
        product_count = random.randint(1, 10)
        product_price = random.randint(15, 45)
        amount = product_count * product_price + random.randint(-7, 0)
        new_datetime = last_time + timedelta(minutes=random.randint(1, 60))
        try:
            transaction = Transaction.add_product(
                amount,
                user.id,
                product.id,
                product_price,
                product_count,
                time=new_datetime,
            )
        except Exception:
            if i > TRANSACTION_GENERATOR_EXCEPTION_LIMIT:
                raise RuntimeError(
                    "Too many failed attempts to create a valid transaction, consider changing the seed",
                )
            continue
        return transaction


def random_adjust_balance_transaction(sql_session: Session, last_time: datetime) -> Transaction:
    i = 0
    while True:
        i += 1
        user = random.choice(sql_session.query(User).all())
        amount = random.randint(-50, 100)
        if amount == 0:
            amount = 1
        new_datetime = last_time + timedelta(minutes=random.randint(1, 60))
        try:
            transaction = Transaction.adjust_balance(
                amount,
                user.id,
                time=new_datetime,
            )
        except Exception:
            if i > TRANSACTION_GENERATOR_EXCEPTION_LIMIT:
                raise RuntimeError(
                    "Too many failed attempts to create a valid transaction, consider changing the seed",
                )
            continue
        return transaction


def random_adjust_interest_transaction(sql_session: Session, last_time: datetime) -> Transaction:
    i = 0
    while True:
        i += 1
        user = random.choice(sql_session.query(User).all())
        amount = random.randint(100, 105)
        new_datetime = last_time + timedelta(minutes=random.randint(1, 60))
        try:
            transaction = Transaction.adjust_interest(
                amount,
                user.id,
                time=new_datetime,
            )
        except Exception:
            if i > TRANSACTION_GENERATOR_EXCEPTION_LIMIT:
                raise RuntimeError(
                    "Too many failed attempts to create a valid transaction, consider changing the seed",
                )
            continue
        return transaction


def random_adjust_penalty_transaction(sql_session: Session, last_time: datetime) -> Transaction:
    i = 0
    while True:
        i += 1
        user = random.choice(sql_session.query(User).all())
        penalty_multiplier_percent = random.randint(100, 200)
        penalty_threshold = random.randint(-150, -50)
        new_datetime = last_time + timedelta(minutes=random.randint(1, 60))
        try:
            transaction = Transaction.adjust_penalty(
                penalty_multiplier_percent,
                penalty_threshold,
                user.id,
                time=new_datetime,
            )
        except Exception:
            if i > TRANSACTION_GENERATOR_EXCEPTION_LIMIT:
                raise RuntimeError(
                    "Too many failed attempts to create a valid transaction, consider changing the seed",
                )
            continue
        return transaction


def random_adjust_stock_transaction(sql_session: Session, last_time: datetime) -> Transaction:
    i = 0
    while True:
        i += 1
        user = random.choice(sql_session.query(User).all())
        product = random.choice(sql_session.query(Product).all())
        stock_change = random.randint(-5, 6)
        if stock_change == 0:
            stock_change = 1
        new_datetime = last_time + timedelta(minutes=random.randint(1, 60))
        try:
            transaction = Transaction.adjust_stock(
                user_id=user.id,
                product_id=product.id,
                product_count=stock_change,
                time=new_datetime,
            )
        except Exception:
            if i > TRANSACTION_GENERATOR_EXCEPTION_LIMIT:
                raise RuntimeError(
                    "Too many failed attempts to create a valid transaction, consider changing the seed",
                )
            continue
        return transaction


def random_buy_product_transaction(sql_session: Session, last_time: datetime) -> Transaction:
    i = 0
    while True:
        i += 1
        user = random.choice(sql_session.query(User).all())
        product = random.choice(sql_session.query(Product).all())
        product_count = random.randint(1, 5)
        new_datetime = last_time + timedelta(minutes=random.randint(1, 60))
        try:
            transaction = Transaction.buy_product(
                user_id=user.id,
                product_id=product.id,
                product_count=product_count,
                time=new_datetime,
            )
        except Exception:
            if i > TRANSACTION_GENERATOR_EXCEPTION_LIMIT:
                raise RuntimeError(
                    "Too many failed attempts to create a valid transaction, consider changing the seed",
                )
            continue
        return transaction


def random_joint_transaction(sql_session: Session, last_time: datetime) -> list[Transaction]:
    i = 0
    while True:
        i += 1
        user_count = random.randint(2, 4)
        users = random.sample(sql_session.query(User).all(), k=user_count)
        product = random.choice(sql_session.query(Product).all())
        product_count = random.randint(1, 5)
        new_datetime = last_time + timedelta(minutes=random.randint(1, 60))

        try:
            transactions = joint_buy_product(
                sql_session,
                product=product,
                product_count=product_count,
                instigator=users[0],
                users=users,
                time=new_datetime,
            )
        except Exception:
            if i > TRANSACTION_GENERATOR_EXCEPTION_LIMIT:
                raise RuntimeError(
                    "Too many failed attempts to create a valid transaction, consider changing the seed",
                )
            continue
        return transactions


def random_transfer_transaction(sql_session: Session, last_time: datetime) -> Transaction:
    i = 0
    while True:
        i += 1
        sender, receiver = random.sample(sql_session.query(User).all(), k=2)
        amount = random.randint(1, 50)
        new_datetime = last_time + timedelta(minutes=random.randint(1, 60))
        try:
            transaction = Transaction.transfer(
                amount,
                sender.id,
                receiver.id,
                time=new_datetime,
            )
        except Exception:
            if i > TRANSACTION_GENERATOR_EXCEPTION_LIMIT:
                raise RuntimeError(
                    "Too many failed attempts to create a valid transaction, consider changing the seed",
                )
            continue
        return transaction


def random_throw_product_transaction(sql_session: Session, last_time: datetime) -> Transaction:
    i = 0
    while True:
        i += 1
        user = random.choice(sql_session.query(User).all())
        product = random.choice(sql_session.query(Product).all())
        product_count = random.randint(1, 5)
        new_datetime = last_time + timedelta(minutes=random.randint(1, 60))
        try:
            transaction = Transaction.throw_product(
                user_id=user.id,
                product_id=product.id,
                product_count=product_count,
                time=new_datetime,
            )
        except Exception:
            if i > TRANSACTION_GENERATOR_EXCEPTION_LIMIT:
                raise RuntimeError(
                    "Too many failed attempts to create a valid transaction, consider changing the seed",
                )
            continue
        return transaction


RANDOM_GENERATORS = {
    TransactionType.ADD_PRODUCT: random_add_product_transaction,
    TransactionType.ADJUST_BALANCE: random_adjust_balance_transaction,
    TransactionType.ADJUST_INTEREST: random_adjust_interest_transaction,
    TransactionType.ADJUST_PENALTY: random_adjust_penalty_transaction,
    TransactionType.ADJUST_STOCK: random_adjust_stock_transaction,
    TransactionType.BUY_PRODUCT: random_buy_product_transaction,
    TransactionType.JOINT: random_joint_transaction,
    TransactionType.TRANSFER: random_transfer_transaction,
    TransactionType.THROW_PRODUCT: random_throw_product_transaction,
}

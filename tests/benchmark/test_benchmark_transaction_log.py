import pytest
from sqlalchemy.orm import Session

from dibbler.models import Product, User
from dibbler.queries import transaction_log
from tests.benchmark.benchmark_settings import BENCHMARK_ITERATIONS, BENCHMARK_ROUNDS
from tests.benchmark.helpers import generate_random_transactions, insert_users_and_products


@pytest.mark.benchmark(group="transaction_log")
@pytest.mark.parametrize(
    "transaction_count",
    [
        100,
        500,
        1000,
        2000,
        5000,
        10000,
    ],
)
def test_benchmark_transaction_log(
    benchmark,
    sql_session: Session,
    transaction_count: int,
) -> None:
    users, products = insert_users_and_products(sql_session)

    transactions = generate_random_transactions(
        sql_session,
        transaction_count,
    )

    sql_session.add_all(transactions)
    sql_session.commit()

    benchmark.pedantic(
        query_transaction_log,
        args=(
            sql_session,
            products,
            users,
        ),
        iterations=BENCHMARK_ITERATIONS,
        rounds=BENCHMARK_ROUNDS,
    )


def query_transaction_log(sql_session: Session, products: list[Product], users: list[User]) -> None:
    for user in users:
        transaction_log(sql_session, user=user)

    for product in products:
        transaction_log(sql_session, product=product)

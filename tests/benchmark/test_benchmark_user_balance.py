import pytest
from sqlalchemy.orm import Session

from dibbler.models import User
from dibbler.queries import update_cache, user_balance
from tests.benchmark.benchmark_settings import BENCHMARK_ITERATIONS, BENCHMARK_ROUNDS
from tests.benchmark.helpers import generate_random_transactions, insert_users_and_products


@pytest.mark.benchmark(group="user_balance")
@pytest.mark.parametrize(
    "transaction_count",
    [
        100,
        500,
        1000,
        1500,
        2000,
    ],
)
def test_benchmark_user_balance(
    benchmark,
    sql_session: Session,
    transaction_count: int,
) -> None:
    users, _products = insert_users_and_products(sql_session)

    transactions = generate_random_transactions(
        sql_session,
        transaction_count,
    )

    sql_session.add_all(transactions)
    sql_session.commit()

    benchmark.pedantic(
        query_all_users_balance,
        args=(sql_session, users),
        iterations=BENCHMARK_ITERATIONS,
        rounds=BENCHMARK_ROUNDS,
    )


@pytest.mark.benchmark(group="user_balance")
@pytest.mark.parametrize(
    "transaction_count",
    [
        1000,
        1500,
        2000,
    ],
)
def test_benchmark_user_balance_cache_every_500(
    benchmark,
    sql_session: Session,
    transaction_count: int,
) -> None:
    users, _products = insert_users_and_products(sql_session)

    transactions = generate_random_transactions(
        sql_session,
        transaction_count,
    )

    for i in range(0, len(transactions), 500):
        update_cache(sql_session)

        sql_session.add_all(transactions[i : i + 500])
        sql_session.commit()

    benchmark.pedantic(
        query_all_users_balance,
        args=(sql_session, users),
        iterations=BENCHMARK_ITERATIONS,
        rounds=BENCHMARK_ROUNDS,
    )


def query_all_users_balance(sql_session: Session, users: list[User]) -> None:
    for user in users:
        user_balance(sql_session, user, use_cache=False)

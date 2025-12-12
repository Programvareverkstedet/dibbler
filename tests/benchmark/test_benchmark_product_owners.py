import pytest
from sqlalchemy.orm import Session

from dibbler.models import Product, TransactionType
from dibbler.queries import product_owners
from tests.benchmark.benchmark_settings import BENCHMARK_ITERATIONS, BENCHMARK_ROUNDS
from tests.benchmark.helpers import generate_random_transactions, insert_users_and_products


@pytest.mark.benchmark(group="product_owners")
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
def test_benchmark_product_owners(
    benchmark,
    sql_session: Session,
    transaction_count: int,
) -> None:
    _users, products = insert_users_and_products(sql_session)

    transactions = generate_random_transactions(
        sql_session,
        transaction_count,
        transaction_type_filter=[
            TransactionType.ADD_PRODUCT,
            TransactionType.ADJUST_STOCK,
            TransactionType.BUY_PRODUCT,
            TransactionType.JOINT,
            TransactionType.THROW_PRODUCT,
        ],
    )

    sql_session.add_all(transactions)
    sql_session.commit()

    benchmark.pedantic(
        query_all_product_owners,
        args=(sql_session, products),
        iterations=BENCHMARK_ITERATIONS,
        rounds=BENCHMARK_ROUNDS,
    )


def query_all_product_owners(sql_session: Session, products: list[Product]) -> None:
    for product in products:
        product_owners(sql_session, product, use_cache=False)

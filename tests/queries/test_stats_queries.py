from collections.abc import Callable, Iterator, Sequence
from datetime import datetime, timedelta
from functools import partial
from typing import NamedTuple, assert_never

import pytest
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from dibbler.models import Product, ProductLog, TransactionLog, User, UserLog
from dibbler.queries import (
    add_stock,
    adjust_balance,
    adjust_stock,
    buy_products,
    create_product,
    create_user,
    merge_products,
    transfer,
)
from dibbler.queries.stats import (
    daily_stats_list,
    daily_stats_stream,
    products_top_selling_list,
    products_top_selling_stream,
    summarize_product_stock,
    summarize_user_balance,
    users_top_depositing_list,
    users_top_depositing_stream,
    users_top_restocking_list,
    users_top_restocking_stream,
    users_top_spending_list,
    users_top_spending_stream,
    users_top_withdrawing_list,
    users_top_withdrawing_stream,
)

STATS_QUERIES: list[Callable[[Session], object]] = [
    daily_stats_list,
    products_top_selling_list,
    products_top_selling_list,
    users_top_depositing_list,
    users_top_restocking_list,
    users_top_spending_list,
    summarize_product_stock,
    summarize_user_balance,
]

STREAMABLE_QUERIES = [
    pytest.param(
        products_top_selling_stream,
        partial(products_top_selling_list, limit=None),
        id="products_top_selling_list",
    ),
    pytest.param(
        partial(daily_stats_stream, after_time=None),
        partial(daily_stats_list, after_time=None),
        id="daily_stats_list(after_time=None)",
    ),
    pytest.param(
        partial(products_top_selling_stream, rank_by_credit=True),
        partial(products_top_selling_list, limit=None, rank_by_credit=True),
        id="products_top_selling_list(rank_by_credit)",
    ),
    pytest.param(
        partial(products_top_selling_stream, include_hidden=True),
        partial(products_top_selling_list, limit=None, include_hidden=True),
        id="products_top_selling_list(include_hidden)",
    ),
    *(
        pytest.param(stream_function, partial(list_function, limit=None), id=list_function.__name__)
        for stream_function, list_function in [
            (users_top_depositing_stream, users_top_depositing_list),
            (users_top_restocking_stream, users_top_restocking_list),
            (users_top_spending_stream, users_top_spending_list),
            (users_top_withdrawing_stream, users_top_withdrawing_list),
        ]
    ),
]


class CreateUser(NamedTuple):
    name: str
    credit: int = 0


class CreateProduct(NamedTuple):
    bar_code: str
    name: str
    price: int
    stock: int = 0
    hidden: bool = False
    user: str | None = None


class Buy(NamedTuple):
    buyers: dict[str, int]
    """Buyer name -> penalty"""
    products: dict[str, int]
    """Product name -> amount"""


class AddStock(NamedTuple):
    users: list[str]
    products: dict[str, tuple[int, int]]
    """Product name -> (amount, paid)"""


class Deposit(NamedTuple):
    user: str
    amount: int


class Withdraw(NamedTuple):
    user: str
    amount: int


class Transfer(NamedTuple):
    from_user: str
    to_user: str
    amount: int


class AdjustStock(NamedTuple):
    user: str
    product: str
    delta: int


class Merge(NamedTuple):
    user: str
    source: str
    target: str


Event = (
    CreateUser
    | CreateProduct
    | Buy
    | AddStock
    | Deposit
    | Withdraw
    | Transfer
    | AdjustStock
    | Merge
)

# (days ago, event)
TIMELINE: list[tuple[int, Event]] = [
    # Inactive users
    (1900, CreateUser("olduser", credit=400)),
    (1900, CreateUser("olddebtor")),
    (1850, Withdraw("olddebtor", 150)),
    (500, CreateUser("alice", credit=1000)),
    (500, CreateUser("bob", credit=50)),
    (500, CreateUser("eve", credit=-200)),

    # Never active, zero balance
    (500, CreateUser("mallory")),
    (500, CreateProduct("1111111111", "Pepsi", 10, stock=20, user="alice")),
    (500, CreateProduct("2222222222", "Cola", 15, stock=5, user="alice")),
    (500, CreateProduct("3333333333", "Solo", 12)),
    (500, CreateProduct("4444444444", "Fanta", 8, stock=3, hidden=True, user="alice")),

    (400, CreateProduct("5555555555", "Cola Zero", 15)),
    (400, AddStock(["bob"], {"Cola Zero": (4, 60)})),
    (365, Buy({"alice": 1}, {"Cola Zero": 2})),
    (200, AddStock(["bob"], {"Solo": (12, 120)})),
    (60, Buy({"bob": 1}, {"Solo": 1})),
    (45, Buy({"eve": 1}, {"Cola Zero": 1})),

    # Beginning of last month
    (30, Deposit("eve", 200)),
    (29, Buy({"alice": 1, "bob": 2}, {"Pepsi": 3})),
    (20, Buy({"alice": 1}, {"Pepsi": 2, "Cola": 1})),

    (14, Merge("alice", "Cola Zero", "Cola")),

    # Buying so much cola that it goes into the negative
    (10, Buy({"eve": 1}, {"Cola": 10})),
    (7, AddStock(["alice"], {"Pepsi": (10, 100), "Solo": (5, 60)})),
    (7, AddStock(["alice", "bob"], {"Solo": (6, 72)})),
    (3, CreateUser("dave")),
    (3, Deposit("dave", 300)),
    (3, Deposit("bob", 300)),
    (2, Withdraw("alice", 50)),
    (2, AdjustStock("alice", "Pepsi", -1)),
    (1, Transfer("alice", "eve", 100)),

    # A new product that has never been in stock
    (1, CreateProduct("6666666666", "Urge", 20)),
    (0, Buy({"dave": 1}, {"Pepsi": 1})),
    (0, Buy({"bob": 1, "eve": 1}, {"Solo": 2, "Pepsi": 1})),
]  # fmt: skip


def _apply(
    sql_session: Session,
    event: Event,
    users: dict[str, User],
    products: dict[str, Product],
) -> None:
    match event:
        case CreateUser(name, credit):
            users[name] = create_user(sql_session, name, credit=credit)
        case CreateProduct(bar_code, name, price, stock, hidden, user):
            products[name] = create_product(
                sql_session,
                bar_code,
                name,
                price,
                stock,
                hidden,
                users[user] if user is not None else None,
            )
        case Buy(buyers, bought):
            buy_products(
                sql_session,
                [(users[name], penalty) for name, penalty in buyers.items()],
                [(products[name], amount) for name, amount in bought.items()],
            )
        case AddStock(restockers, added):
            add_stock(
                sql_session,
                [users[name] for name in restockers],
                [(products[name], amount, paid) for name, (amount, paid) in added.items()],
                total_price=sum(paid for _amount, paid in added.values()),
            )
        case Deposit(user, amount):
            adjust_balance(sql_session, users[user], -amount)
        case Withdraw(user, amount):
            adjust_balance(sql_session, users[user], amount)
        case Transfer(from_user, to_user, amount):
            transfer(sql_session, users[from_user], users[to_user], amount)
        case AdjustStock(user, product, delta):
            adjust_stock(sql_session, users[user], products[product], delta)
        case Merge(user, source, target):
            merge_products(sql_session, users[user], products.pop(source), products[target])
        case _:
            assert_never(event)


# returns the stock of each product at the end of each days ago in the timeline.
def _populate(sql_session: Session) -> dict[int, dict[str, int]]:
    users: dict[str, User] = {}
    products: dict[str, Product] = {}
    stock_history: dict[int, dict[str, int]] = {}

    for days_ago, event in TIMELINE:
        last_ids = {
            log: sql_session.scalar(select(func.coalesce(func.max(log.id), 0)))
            for log in (TransactionLog, UserLog, ProductLog)
        }
        _apply(sql_session, event, users, products)
        sql_session.flush()
        for log, last_id in last_ids.items():
            sql_session.execute(
                update(log)
                .where(log.id > last_id)
                .values(time=datetime.now() - timedelta(days=days_ago)),
            )
        stock_history[days_ago] = {name: product.stock for name, product in products.items()}

    # Legacy user without any log entries
    sql_session.add(User("legacy", None, credit=75))
    sql_session.flush()

    return stock_history


# NOTE: This reuses the same database session for all tests in this module.
#       If you were to modify the database in a test, it would affect the rest.
#       All of the tested queries are read-only, so this should be safe.
@pytest.fixture(scope="module")
def populated_session(module_sql_session: Session) -> Session:
    _populate(module_sql_session)
    return module_sql_session


@pytest.mark.parametrize(
    "query_function",
    STATS_QUERIES,
    ids=lambda query: query.__name__,
)
def test_stats_query_empty(
    sql_session: Session,
    query_function: Callable[[Session], object],
) -> None:
    query_function(sql_session)


@pytest.mark.parametrize(
    "query_function",
    STATS_QUERIES,
    ids=lambda query: query.__name__,
)
def test_stats_query_populated(
    populated_session: Session,
    query_function: Callable[[Session], object],
) -> None:
    query_function(populated_session)


@pytest.mark.parametrize(("stream_function", "list_function"), STREAMABLE_QUERIES)
def test_stats_query_streamed_matches_list(
    populated_session: Session,
    stream_function: Callable[..., Iterator[object]],
    list_function: Callable[[Session], Sequence[object]],
) -> None:
    streamed = list(stream_function(populated_session, chunk_size=2))
    assert streamed == list_function(populated_session)

from sqlalchemy import insert, select
from sqlalchemy.orm import Session

from dibbler.models import LastCacheTransaction, ProductCache, Transaction, UserCache
from dibbler.queries.affected_products import affected_products
from dibbler.queries.affected_users import affected_users
from dibbler.queries.product_price import product_price
from dibbler.queries.product_stock import product_stock
from dibbler.queries.user_balance import user_balance


def update_cache(
    sql_session: Session,
    use_cache: bool = True,
) -> None:
    """
    Update the cache used for searching products.

    If `use_cache` is False, the cache will be rebuilt from scratch.
    """

    last_transaction = sql_session.scalars(
        select(Transaction).order_by(Transaction.time.desc()).limit(1),
    ).one_or_none()

    print(last_transaction)

    if last_transaction is None:
        # No transactions exist, nothing to update
        return

    if use_cache:
        last_cache_transaction = sql_session.scalars(
            select(LastCacheTransaction)
            .join(Transaction, LastCacheTransaction.transaction_id == Transaction.id)
            .order_by(Transaction.time.desc())
            .limit(1),
        ).one_or_none()
        if last_cache_transaction is not None:
            last_cache_transaction = last_cache_transaction.transaction
    else:
        last_cache_transaction = None

    if last_cache_transaction is not None and last_cache_transaction.id == last_transaction.id:
        # Cache is already up to date
        return

    users = affected_users(
        sql_session,
        after_transaction=last_cache_transaction,
        after_inclusive=False,
        until_transaction=last_transaction,
    )
    products = affected_products(
        sql_session,
        after_transaction=last_cache_transaction,
        after_inclusive=False,
        until_transaction=last_transaction,
    )

    user_balances = {}
    for user in users:
        x = user_balance(
            sql_session,
            user,
            use_cache=use_cache,
            until_transaction=last_transaction,
        )
        user_balances[user.id] = x

    product_stocks = {}
    product_prices = {}
    for product in products:
        product_stocks[product.id] = product_stock(
            sql_session,
            product,
            use_cache=use_cache,
            until_transaction=last_transaction,
        )
        product_prices[product.id] = product_price(
            sql_session,
            product,
            use_cache=use_cache,
            until_transaction=last_transaction,
        )

    next_cache_transaction = LastCacheTransaction(transaction_id=last_transaction.id)
    sql_session.add(next_cache_transaction)
    sql_session.flush()

    if not len(users) == 0:
        sql_session.execute(
            insert(UserCache),
            [
                {
                    "user_id": user.id,
                    "balance": user_balances[user.id],
                    "last_cache_transaction_id": next_cache_transaction.id,
                }
                for user in users
            ],
        )

    if not len(products) == 0:
        sql_session.execute(
            insert(ProductCache),
            [
                {
                    "product_id": product.id,
                    "stock": product_stocks[product.id],
                    "price": product_prices[product.id],
                    "last_cache_transaction_id": next_cache_transaction.id,
                }
                for product in products
            ],
        )

    sql_session.commit()

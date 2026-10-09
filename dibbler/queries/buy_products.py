from datetime import datetime

from sqlalchemy.orm import Session

from dibbler import economy
from dibbler.models import (
    Product,
    Purchase,
    PurchaseEntry,
    Transaction,
    TransactionLog,
    TransactionLogProduct,
    TransactionLogUser,
    User,
)
from dibbler.models.enums import TransactionLogEntryType

MAX_BUY_AMOUNT_TOTAL = 999


def buy_products(
    sql_session: Session,
    buyers: list[tuple[User, int]],
    products: list[tuple[Product, int]],
) -> Purchase:
    if not buyers:
        raise ValueError("At least one buyer must be specified.")

    if not products:
        raise ValueError("At least one product must be specified.")

    if any(penalty < 1 for _, penalty in buyers):
        raise ValueError("Penalty must be at least 1.")

    penalty_by_user: dict[User, int] = {}
    for user, penalty in buyers:
        if user in penalty_by_user and penalty_by_user[user] != penalty:
            raise ValueError("A buyer cannot have more than one penalty in the same purchase.")
        penalty_by_user[user] = penalty

    if any(amount <= 0 for _, amount in products):
        raise ValueError("Product amounts must be positive.")

    if sum(amount for _, amount in products) > MAX_BUY_AMOUNT_TOTAL:
        raise ValueError(f"Total product amount must be at most {MAX_BUY_AMOUNT_TOTAL}.")

    total_price = economy.purchase_price(products)
    charges = economy.buyer_charges(total_price, buyers)

    for user, _penalty, charge in charges:
        user.credit -= charge

    for product, amount in products:
        product.stock -= amount

    header = TransactionLog(type=TransactionLogEntryType.BUY_PRODUCT, time=datetime.now())
    sql_session.add(header)
    sql_session.add_all(
        TransactionLogUser(transaction=header, user=user, amount=charge, penalty=penalty)
        for user, penalty, charge in charges
    )
    sql_session.add_all(
        TransactionLogProduct(
            transaction=header,
            product=product,
            amount=-amount,
            price_at_time=product.price,
        )
        for product, amount in products
    )

    # NOTE: Only kept around for backwards compatibility until the legacy tables are dropped.
    with sql_session.no_autoflush:
        purchase = Purchase()
        purchase.time = header.time
        purchase.price = total_price
        sql_session.add(purchase)
        for user, penalty, charge in charges:
            transaction = Transaction(user, charge, purchase=purchase, penalty=penalty)
            transaction.time = header.time
            sql_session.add(transaction)
        sql_session.add_all(
            PurchaseEntry(purchase, product, amount) for product, amount in products
        )
    sql_session.flush()

    return purchase

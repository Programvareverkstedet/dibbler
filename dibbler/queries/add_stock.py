from datetime import datetime
from math import ceil

from sqlalchemy.orm import Session

from dibbler.lib.helpers import simplify_shares
from dibbler.models import (
    Product,
    ProductLog,
    Purchase,
    PurchaseEntry,
    Transaction,
    TransactionLog,
    TransactionLogProduct,
    TransactionLogUser,
    User,
)
from dibbler.models.enums import ProductLogEntryType, TransactionLogEntryType

from .adjust_stock import adjust_stock

NEGATIVE_STOCK_RESET_DESCRIPTION = "Autonullstilling av negativ beholdning ved innkjøp"
MAX_ADD_AMOUNT_PER_PRODUCT = 999


def add_stock(
    sql_session: Session,
    users: list[User],
    products: list[tuple[Product, int, int]],
    total_price: int,
    description: str | None = None,
) -> Purchase:
    if not users:
        raise ValueError("At least one user must be specified.")

    if not products:
        raise ValueError("At least one product must be specified.")

    if total_price < 0:
        raise ValueError("Total price must not be negative.")

    if any(amount <= 0 for _, amount, _ in products):
        raise ValueError("Product amounts must be positive.")

    if any(amount > MAX_ADD_AMOUNT_PER_PRODUCT for _, amount, _ in products):
        raise ValueError(f"Product amounts must be at most {MAX_ADD_AMOUNT_PER_PRODUCT}.")

    if any(paid_amount < 0 for _, _, paid_amount in products):
        raise ValueError("Paid amounts must not be negative.")

    # TODO: remove this `min` once we get rid of `Transaction`
    max_description_length = min(Transaction.description_length, TransactionLog.description_length)
    if description is not None and len(description) > max_description_length:
        raise ValueError(f"Description must be at most {max_description_length} characters.")

    users = simplify_shares(users)

    for product, _amount, _paid_amount in products:
        if product.stock < 0:
            adjust_stock(
                sql_session,
                users[0],
                product,
                -product.stock,
                description=NEGATIVE_STOCK_RESET_DESCRIPTION,
            )

    unhidden = [product for product, _amount, _paid_amount in products if product.hidden]

    for product, amount, paid_amount in products:
        value = max(product.stock, 0) * product.price + paid_amount
        product.price = int(ceil(float(value) / (max(product.stock, 0) + amount)))
        product.stock += amount
        product.hidden = False

    with sql_session.no_autoflush:
        purchase = Purchase()
        sql_session.add(purchase)

        transactions = [
            Transaction(user, purchase=purchase, description=description) for user in users
        ]
        sql_session.add_all(transactions)
        sql_session.add_all(
            PurchaseEntry(purchase, product, -amount) for product, amount, _paid_amount in products
        )

        purchase.perform_soft_purchase(-total_price, round_up=False)
    sql_session.flush()

    header = TransactionLog(
        type=TransactionLogEntryType.ADD_PRODUCT,
        time=datetime.now(),
        description=description,
    )
    sql_session.add(header)
    sql_session.add_all(
        TransactionLogUser(transaction=header, user=transaction.user, amount=transaction.amount)
        for transaction in transactions
    )
    sql_session.add_all(
        TransactionLogProduct(
            transaction=header,
            product=product,
            amount=amount,
            price_at_time=product.price,
        )
        for product, amount, _paid_amount in products
    )
    sql_session.add_all(
        ProductLog(
            type=ProductLogEntryType.EDIT,
            time=header.time,
            product_id=product.id,
            hidden=False,
        )
        for product in unhidden
    )
    sql_session.flush()

    return purchase

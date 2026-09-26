from math import ceil

from sqlalchemy.orm import Session

from dibbler.models import Product, Purchase, PurchaseEntry, Transaction, User


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

    for product, amount, paid_amount in products:
        value = max(product.stock, 0) * product.price + paid_amount
        product.price = int(ceil(float(value) / (max(product.stock, 0) + amount)))
        product.stock = max(amount, product.stock + amount)
        product.hidden = False

    purchase = Purchase()
    sql_session.add(purchase)

    sql_session.add_all(
        Transaction(user, purchase=purchase, description=description) for user in users
    )
    sql_session.add_all(
        PurchaseEntry(purchase, product, -amount) for product, amount, _paid_amount in products
    )

    purchase.perform_soft_purchase(-total_price, round_up=False)
    sql_session.flush()

    return purchase

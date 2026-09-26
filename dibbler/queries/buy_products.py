from sqlalchemy.orm import Session

from dibbler.models import Product, Purchase, PurchaseEntry, Transaction, User


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

    purchase = Purchase()
    sql_session.add(purchase)

    sql_session.add_all(
        Transaction(user, purchase=purchase, penalty=penalty) for user, penalty in buyers
    )
    sql_session.add_all(PurchaseEntry(purchase, product, amount) for product, amount in products)

    purchase.perform_purchase()
    sql_session.flush()

    return purchase

from datetime import datetime

from sqlalchemy.orm import Session

from dibbler import economy
from dibbler.models import (
    Product,
    ProductLog,
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
) -> None:
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

    if description is not None and len(description) > TransactionLog.description_length:
        raise ValueError(
            f"Description must be at most {TransactionLog.description_length} characters.",
        )

    user_credits = economy.restock_credits(total_price, users)

    for product, _amount, _paid_amount in products:
        reset = economy.stock_reset_before_restock(product.stock)
        if reset != 0:
            adjust_stock(
                sql_session,
                users[0],
                product,
                reset,
                description=NEGATIVE_STOCK_RESET_DESCRIPTION,
            )

    edits: list[tuple[Product, int | None, bool | None]] = []

    for product, amount, paid_amount in products:
        price = economy.restock_price(product.stock, product.price, amount, paid_amount)

        edited_price = price if price != product.price else None
        edited_hidden = False if product.hidden else None
        if edited_price is not None or edited_hidden is not None:
            edits.append((product, edited_price, edited_hidden))

        product.price = price
        product.stock += amount
        product.hidden = False

    for user, credit in user_credits:
        user.credit += credit

    header = TransactionLog(
        type=TransactionLogEntryType.ADD_PRODUCT,
        time=datetime.now(),
        description=description,
    )
    sql_session.add(header)
    sql_session.add_all(
        TransactionLogUser(transaction=header, user=user, amount=-credit)
        for user, credit in user_credits
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
            price=edited_price,
            hidden=edited_hidden,
        )
        for product, edited_price, edited_hidden in edits
    )
    sql_session.flush()

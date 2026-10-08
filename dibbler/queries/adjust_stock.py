from datetime import datetime

from sqlalchemy.orm import Session

from dibbler.models import (
    Product,
    TransactionLog,
    TransactionLogProduct,
    TransactionLogUser,
    User,
)
from dibbler.models.enums import TransactionLogEntryType

MIN_ADJUSTED_STOCK = 0
MAX_ADJUSTED_STOCK = 9999


def adjust_stock(
    sql_session: Session,
    user: User,
    product: Product,
    delta: int,
    description: str | None = None,
) -> Product:
    if delta == 0:
        raise ValueError("Delta must be non-zero.")

    if not MIN_ADJUSTED_STOCK <= product.stock + delta <= MAX_ADJUSTED_STOCK:
        raise ValueError(
            f"Resulting stock must be between {MIN_ADJUSTED_STOCK} and {MAX_ADJUSTED_STOCK}.",
        )

    if description is not None and len(description) > TransactionLog.description_length:
        raise ValueError(
            f"Description must be at most {TransactionLog.description_length} characters.",
        )

    product.stock += delta

    header = TransactionLog(
        type=TransactionLogEntryType.ADJUST_STOCK,
        time=datetime.now(),
        description=description,
    )
    sql_session.add(header)
    sql_session.add(
        TransactionLogUser(
            transaction=header,
            user=user,
        ),
    )
    sql_session.add(
        TransactionLogProduct(
            transaction=header,
            product=product,
            amount=delta,
            price_at_time=product.price,
        ),
    )
    sql_session.flush()

    return product

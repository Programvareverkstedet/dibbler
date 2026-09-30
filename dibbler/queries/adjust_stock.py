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


def adjust_stock(
    sql_session: Session,
    user: User,
    product: Product,
    delta: int,
    description: str | None = None,
) -> Product:
    if delta == 0:
        raise ValueError("Delta must be non-zero.")

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

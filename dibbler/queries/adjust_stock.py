from datetime import datetime

from sqlalchemy.orm import Session

from dibbler.models import Product, TransactionLog, TransactionLogProduct
from dibbler.models.enums import TransactionLogEntryType


def adjust_stock(sql_session: Session, product: Product, delta: int) -> Product:
    if delta == 0:
        raise ValueError("Delta must be non-zero.")

    product.stock += delta

    header = TransactionLog(type=TransactionLogEntryType.ADJUST_STOCK, time=datetime.now())
    sql_session.add(header)
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

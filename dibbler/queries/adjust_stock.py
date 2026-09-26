from sqlalchemy.orm import Session

from dibbler.models import Product


def adjust_stock(sql_session: Session, product: Product, delta: int) -> Product:
    if delta == 0:
        raise ValueError("Delta must be non-zero.")

    product.stock += delta
    sql_session.flush()

    return product

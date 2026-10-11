from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from dibbler.models import ProductBarcode


def check_barcode_available(sql_session: Session, barcode: str) -> None:
    """Raise a `ValueError` if a product already has this barcode."""
    if sql_session.scalar(select(exists().where(ProductBarcode.code == barcode))):
        raise ValueError("Barcode already in use.")

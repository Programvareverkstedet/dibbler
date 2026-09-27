import pytest
from sqlalchemy.orm import Session

from dibbler.models import Product, TransactionLog
from dibbler.models.enums import TransactionLogEntryType
from dibbler.queries import adjust_stock


def _make_product(sql_session: Session, stock: int = 10) -> Product:
    product = Product("1234567890", "Cola", 15, stock=stock)
    sql_session.add(product)
    sql_session.flush()
    return product


def test_adjust_stock_changes_stock_by_delta(sql_session: Session) -> None:
    product = _make_product(sql_session, stock=10)

    adjust_stock(sql_session, product, 5)
    sql_session.expire_all()
    assert product.stock == 15

    adjust_stock(sql_session, product, -8)
    sql_session.expire_all()
    assert product.stock == 7


def test_adjust_stock_allows_negative_resulting_stock(sql_session: Session) -> None:
    product = _make_product(sql_session, stock=2)

    adjust_stock(sql_session, product, -5)

    sql_session.expire_all()

    assert product.stock == -3


def test_adjust_stock_records_a_transaction_log_entry(sql_session: Session) -> None:
    product = _make_product(sql_session)

    adjust_stock(sql_session, product, 5)

    sql_session.expire_all()

    log = sql_session.query(TransactionLog).one()
    assert log.type == TransactionLogEntryType.ADJUST_STOCK


def test_adjust_stock_rejects_zero_delta(sql_session: Session) -> None:
    product = _make_product(sql_session)

    with pytest.raises(ValueError, match="Delta must be non-zero"):
        adjust_stock(sql_session, product, 0)

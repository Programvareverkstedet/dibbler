import pytest
from sqlalchemy.orm import Session

from dibbler.models import Product, TransactionLog, User
from dibbler.models.enums import TransactionLogEntryType
from dibbler.queries import adjust_stock


def _make_product(sql_session: Session, stock: int = 10) -> Product:
    product = Product("1234567890", "Cola", 15, stock=stock)
    sql_session.add(product)
    sql_session.flush()
    return product


def _make_user(sql_session: Session) -> User:
    user = User("alice", None)
    sql_session.add(user)
    sql_session.flush()
    return user


def test_adjust_stock_changes_stock_by_delta(sql_session: Session) -> None:
    product = _make_product(sql_session, stock=10)
    alice = _make_user(sql_session)

    adjust_stock(sql_session, alice, product, 5)
    sql_session.expire_all()
    assert product.stock == 15

    adjust_stock(sql_session, alice, product, -8)
    sql_session.expire_all()
    assert product.stock == 7


def test_adjust_stock_allows_negative_resulting_stock(sql_session: Session) -> None:
    product = _make_product(sql_session, stock=2)
    alice = _make_user(sql_session)

    adjust_stock(sql_session, alice, product, -5)

    sql_session.expire_all()

    assert product.stock == -3


def test_adjust_stock_records_a_transaction_log_entry(sql_session: Session) -> None:
    product = _make_product(sql_session)
    alice = _make_user(sql_session)

    adjust_stock(sql_session, alice, product, 5)

    sql_session.expire_all()

    log = sql_session.query(TransactionLog).one()
    assert log.type == TransactionLogEntryType.ADJUST_STOCK


def test_adjust_stock_records_the_adjusting_user(sql_session: Session) -> None:
    product = _make_product(sql_session)
    alice = _make_user(sql_session)

    adjust_stock(sql_session, alice, product, 5)

    sql_session.expire_all()

    log = sql_session.query(TransactionLog).one()
    assert [(u.user, u.amount) for u in log.users] == [(alice, None)]


@pytest.mark.parametrize(
    ("delta", "description", "error"),
    [
        pytest.param(0, None, "Delta must be non-zero", id="zero-delta"),
        pytest.param(5, "x" * (TransactionLog.description_length + 1), "Description must be at most", id="too-long-description"),
    ],
)  # fmt: skip
def test_invariants(
    sql_session: Session,
    delta: int,
    description: str | None,
    error: str,
) -> None:
    product = _make_product(sql_session, stock=10)
    alice = _make_user(sql_session)

    with pytest.raises(ValueError, match=error):
        adjust_stock(sql_session, alice, product, delta, description=description)

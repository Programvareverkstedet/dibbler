import pytest
from sqlalchemy.orm import Session

from dibbler.models import TransactionLog, User
from dibbler.models.enums import TransactionLogEntryType
from dibbler.queries import adjust_balance


def _make_user(sql_session: Session, credit: int = 100) -> User:
    user = User("alice", None, credit=credit)
    sql_session.add(user)
    sql_session.flush()
    return user


def test_adjust_balance_moves_credit_by_amount(sql_session: Session) -> None:
    user = _make_user(sql_session, credit=100)

    adjust_balance(sql_session, user, 30)
    sql_session.expire_all()
    assert user.credit == 70

    adjust_balance(sql_session, user, -50)
    sql_session.expire_all()
    assert user.credit == 120


def test_adjust_balance_records_a_transaction_for_the_user(sql_session: Session) -> None:
    user = _make_user(sql_session)

    transaction = adjust_balance(sql_session, user, 10, description="manual fix")

    sql_session.expire_all()

    assert transaction in user.transactions
    assert transaction.description == "manual fix"
    assert transaction.time is not None


def test_adjust_balance_records_a_transaction_log_entry(sql_session: Session) -> None:
    user = _make_user(sql_session)

    adjust_balance(sql_session, user, 10, description="manual fix")

    sql_session.expire_all()

    log = sql_session.query(TransactionLog).one()
    assert log.type == TransactionLogEntryType.ADJUST_BALANCE


def test_adjust_balance_rejects_zero_amount(sql_session: Session) -> None:
    user = _make_user(sql_session)

    with pytest.raises(ValueError, match="Amount must be non-zero"):
        adjust_balance(sql_session, user, 0)

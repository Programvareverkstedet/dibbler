import pytest
from sqlalchemy.orm import Session

from dibbler.models import User
from dibbler.queries import transfer


def _make_user(sql_session: Session, name: str, credit: int = 100) -> User:
    user = User(name, None, credit=credit)
    sql_session.add(user)
    sql_session.flush()
    return user


def test_transfer_moves_credit_without_creating_or_destroying_it(sql_session: Session) -> None:
    alice = _make_user(sql_session, "alice", credit=100)
    bob = _make_user(sql_session, "bob", credit=50)

    transfer(sql_session, alice, bob, 30)

    sql_session.expire_all()

    assert alice.credit == 70
    assert bob.credit == 80
    assert alice.credit + bob.credit == 150


def test_transfer_records_linked_transactions_for_both_users(sql_session: Session) -> None:
    alice = _make_user(sql_session, "alice")
    bob = _make_user(sql_session, "bob")

    outgoing, incoming = transfer(sql_session, alice, bob, 30, comment="rent")

    sql_session.expire_all()

    assert outgoing in alice.transactions
    assert incoming in bob.transactions
    assert outgoing.amount == 30
    assert incoming.amount == -30
    assert outgoing.description is not None
    assert "bob" in outgoing.description and "rent" in outgoing.description
    assert incoming.description is not None
    assert "alice" in incoming.description and "rent" in incoming.description


def test_transfer_rejects_non_positive_amount(sql_session: Session) -> None:
    alice = _make_user(sql_session, "alice")
    bob = _make_user(sql_session, "bob")

    with pytest.raises(ValueError, match="Amount must be positive"):
        transfer(sql_session, alice, bob, 0)


def test_transfer_rejects_self_transfer(sql_session: Session) -> None:
    alice = _make_user(sql_session, "alice")

    with pytest.raises(ValueError, match="Cannot transfer to the same user"):
        transfer(sql_session, alice, alice, 10)

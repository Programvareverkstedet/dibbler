import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from dibbler.models import User, UserLog
from dibbler.models.enums import UserLogEntryType
from dibbler.queries import create_user


def test_create_user_persists_a_queryable_user(sql_session: Session) -> None:
    create_user(sql_session, "alice", card="ntnu123", rfid="deadbeef", credit=50)

    sql_session.expire_all()

    user = sql_session.get(User, "alice")
    assert user is not None
    assert user.card == "ntnu123"
    assert user.rfid == "deadbeef"
    assert user.credit == 50


def test_create_user_defaults_to_no_card_rfid_and_zero_credit(sql_session: Session) -> None:
    user = create_user(sql_session, "bob")

    sql_session.expire_all()

    assert user.card is None
    assert user.rfid is None
    assert user.credit == 0


def test_create_user_records_a_create_log_entry(sql_session: Session) -> None:
    create_user(sql_session, "alice", card="ntnu123", rfid="deadbeef", credit=50)

    sql_session.expire_all()

    log = sql_session.query(UserLog).one()
    assert log.type == UserLogEntryType.CREATE
    assert log.user_id == "alice"
    assert log.name == "alice"
    assert log.card == "ntnu123"
    assert log.rfid == "deadbeef"
    assert log.credit == 50


def test_create_user_rejects_empty_name(sql_session: Session) -> None:
    with pytest.raises(ValueError, match="Name cannot be empty"):
        create_user(sql_session, "")


def test_create_user_rejects_duplicate_name(sql_session: Session) -> None:
    create_user(sql_session, "alice")

    with pytest.raises(IntegrityError):
        create_user(sql_session, "alice")


def test_create_user_rejects_uppercase_name(sql_session: Session) -> None:
    with pytest.raises(ValueError, match="lowercase letters only"):
        create_user(sql_session, "Alice")


def test_create_user_rejects_name_with_digits(sql_session: Session) -> None:
    with pytest.raises(ValueError, match="lowercase letters only"):
        create_user(sql_session, "alice1")


def test_create_user_lowercases_card_and_rfid(sql_session: Session) -> None:
    user = create_user(sql_session, "alice", card="NTNU123", rfid="DEADBEEF")

    assert user.card == "ntnu123"
    assert user.rfid == "deadbeef"


def test_create_user_rejects_invalid_card(sql_session: Session) -> None:
    with pytest.raises(ValueError, match="invalid format"):
        create_user(sql_session, "alice", card="not-a-card")


def test_create_user_rejects_invalid_rfid(sql_session: Session) -> None:
    with pytest.raises(ValueError, match="invalid format"):
        create_user(sql_session, "alice", rfid="not-hex!")

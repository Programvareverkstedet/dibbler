from typing import Any

import pytest
from sqlalchemy.orm import Session

from dibbler.models import User, UserLog
from dibbler.models.enums import UserLogEntryType
from dibbler.queries import create_user


def test_create_user_persists_a_queryable_user(sql_session: Session) -> None:
    created = create_user(sql_session, "alice", card="ntnu123", rfid="deadbeef", credit=50)

    sql_session.expire_all()

    user = sql_session.get(User, created.id)
    assert user is not None
    assert user.name == "alice"
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
    created = create_user(sql_session, "alice", card="ntnu123", rfid="deadbeef", credit=50)

    sql_session.expire_all()

    log = sql_session.query(UserLog).one()
    assert log.type == UserLogEntryType.CREATE
    assert log.user_id == created.id
    assert log.name == "alice"
    assert log.card == "ntnu123"
    assert log.rfid == "deadbeef"
    assert log.credit == 50


def test_create_user_lowercases_card_and_rfid(sql_session: Session) -> None:
    user = create_user(sql_session, "alice", card="NTNU123", rfid="DEADBEEF")

    assert user.card == "ntnu123"
    assert user.rfid == "deadbeef"


def test_create_user_allows_several_users_without_card_or_rfid(sql_session: Session) -> None:
    create_user(sql_session, "alice")
    create_user(sql_session, "bob")

    assert sql_session.query(User).count() == 2


@pytest.mark.parametrize(
    ("kwargs", "error"),
    [
        pytest.param({"name": ""}, "Name cannot be empty", id="empty-name"),
        pytest.param({"name": "Bob"}, "lowercase letters only", id="uppercase-name"),
        pytest.param({"name": "bob1"}, "lowercase letters only", id="name-with-digits"),
        pytest.param({"name": "b" * (User.name_length + 1)}, "Name must be at most", id="too-long-name"),
        pytest.param({"name": "alice"}, "already exists", id="duplicate-name"),

        pytest.param({"name": "bob", "card": "not-a-card"}, "invalid format", id="invalid-card"),
        pytest.param({"name": "bob", "card": "1" * (User.card_length + 1)}, "Card number must be at most", id="too-long-card"),
        pytest.param({"name": "bob", "card": "NTNU123"}, "already exists", id="duplicate-card"),

        pytest.param({"name": "bob", "rfid": "not-hex!"}, "invalid format", id="invalid-rfid"),
        pytest.param({"name": "bob", "rfid": "a" * (User.rfid_length + 1)}, "RFID must be at most", id="too-long-rfid"),
        pytest.param({"name": "bob", "rfid": "DEADBEEF"}, "already exists", id="duplicate-rfid"),
    ],
)  # fmt: skip
def test_invariants(sql_session: Session, kwargs: dict[str, Any], error: str) -> None:
    create_user(sql_session, "alice", card="ntnu123", rfid="deadbeef")

    with pytest.raises(ValueError, match=error):
        create_user(sql_session, **kwargs)

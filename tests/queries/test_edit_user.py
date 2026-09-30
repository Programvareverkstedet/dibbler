from typing import Any

import pytest
from sqlalchemy.orm import Session

from dibbler.models import User, UserLog
from dibbler.models.enums import UserLogEntryType
from dibbler.queries import create_user, edit_user


def _make_user(
    sql_session: Session,
    name: str = "alice",
    card: str | None = "ntnu123",
    rfid: str | None = "deadbeef",
) -> User:
    user = User(name, card, rfid)
    sql_session.add(user)
    sql_session.flush()
    return user


def test_edit_user_updates_only_the_given_fields(sql_session: Session) -> None:
    user = _make_user(sql_session)

    edit_user(sql_session, user, card="ntnu456", rfid=None)

    sql_session.expire_all()

    assert user.card == "ntnu456"
    assert user.rfid is None


def test_edit_user_records_the_users_id_as_user_id(sql_session: Session) -> None:
    user = _make_user(sql_session)

    edit_user(sql_session, user, card="ntnu456")

    sql_session.expire_all()

    log = sql_session.query(UserLog).one()
    assert log.type == UserLogEntryType.EDIT
    assert log.user_id == user.id
    assert log.card == "ntnu456"
    assert log.card_touched is True
    assert log.rfid is None
    assert log.rfid_touched is False


def test_edit_user_rename_keeps_the_same_user_id(sql_session: Session) -> None:
    user = create_user(sql_session, "alice")

    edit_user(sql_session, user, name="alicia")

    sql_session.expire_all()

    logs = sql_session.query(UserLog).order_by(UserLog.id).all()
    create_entry, rename_entry = logs
    assert create_entry.user_id == user.id
    assert rename_entry.name == "alicia"
    assert rename_entry.user_id == user.id


def test_edit_user_allows_resubmitting_the_same_name(sql_session: Session) -> None:
    user = _make_user(sql_session, "alice")

    edit_user(sql_session, user, name="alice", card="ntnu456")

    sql_session.expire_all()

    assert user.name == "alice"
    assert user.card == "ntnu456"


def test_edit_user_lowercases_card_and_rfid(sql_session: Session) -> None:
    user = _make_user(sql_session)

    edit_user(sql_session, user, card="NTNU456", rfid="DEADBEEF")

    sql_session.expire_all()

    assert user.card == "ntnu456"
    assert user.rfid == "deadbeef"


def test_edit_user_can_rename(sql_session: Session) -> None:
    user = _make_user(sql_session, "alice")

    edit_user(sql_session, user, name="alicia")

    sql_session.expire_all()

    assert sql_session.get(User, user.id) is user
    assert user.name == "alicia"
    assert sql_session.query(User).filter_by(name="alice").first() is None


def test_edit_user_allows_resubmitting_the_same_card_and_rfid_with_other_changes(
    sql_session: Session,
) -> None:
    user = _make_user(sql_session)

    edit_user(sql_session, user, name="bob", card="ntnu123", rfid="deadbeef")

    sql_session.expire_all()

    assert (user.name, user.card, user.rfid) == ("bob", "ntnu123", "deadbeef")


def test_edit_user_treats_empty_card_and_rfid_as_none(sql_session: Session) -> None:
    alice = _make_user(sql_session, "alice", card=None, rfid=None)
    bob = _make_user(sql_session, "bob", card="ntnu456", rfid="cafebabe")

    edit_user(sql_session, bob, card="", rfid="")

    sql_session.expire_all()

    assert (alice.card, alice.rfid) == (None, None)
    assert (bob.card, bob.rfid) == (None, None)


def test_edit_user_allows_unused_card_and_rfid(sql_session: Session) -> None:
    _make_user(sql_session, "alice")
    bob = _make_user(sql_session, "bob", card="ntnu456", rfid="cafebabe")

    edit_user(sql_session, bob, card="ntnu789", rfid="f00dface")

    sql_session.expire_all()

    assert (bob.card, bob.rfid) == ("ntnu789", "f00dface")


@pytest.mark.parametrize(
    ("kwargs", "error"),
    [
        pytest.param({}, "Nothing to edit", id="nothing"),
        pytest.param({"card": "ntnu456", "rfid": "cafebabe"}, "Nothing to edit", id="same-card-and-rfid"),

        pytest.param({"name": ""}, "Name cannot be empty", id="empty-name"),
        pytest.param({"name": "Robert"}, "lowercase letters only", id="uppercase-name"),
        pytest.param({"name": "b" * (User.name_length + 1)}, "Name must be at most", id="too-long-name"),
        pytest.param({"name": "alice"}, "already exists", id="duplicate-name"),
        pytest.param({"card": "ntnu789", "name": "Robert"}, "lowercase letters only", id="valid-card-invalid-name"),

        pytest.param({"card": "not-a-card"}, "invalid format", id="invalid-card"),
        pytest.param({"card": "1" * (User.card_length + 1)}, "Card number must be at most", id="too-long-card"),
        pytest.param({"card": "NTNU123"}, "already exists", id="duplicate-card"),

        pytest.param({"rfid": "not-hex!"}, "invalid format", id="invalid-rfid"),
        pytest.param({"rfid": "a" * (User.rfid_length + 1)}, "RFID must be at most", id="too-long-rfid"),
        pytest.param({"rfid": "DEADBEEF"}, "already exists", id="duplicate-rfid"),
        pytest.param({"card": "ntnu789", "rfid": "not-hex!"}, "invalid format", id="valid-card-invalid-rfid"),
    ],
)  # fmt: skip
def test_invariants(sql_session: Session, kwargs: dict[str, Any], error: str) -> None:
    _make_user(sql_session, "alice")
    bob = _make_user(sql_session, "bob", card="ntnu456", rfid="cafebabe")

    with pytest.raises(ValueError, match=error):
        edit_user(sql_session, bob, **kwargs)

    sql_session.expire_all()

    assert (bob.name, bob.card, bob.rfid) == ("bob", "ntnu456", "cafebabe")

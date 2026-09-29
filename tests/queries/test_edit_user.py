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


def test_edit_user_rejects_editing_nothing(sql_session: Session) -> None:
    user = _make_user(sql_session)

    with pytest.raises(ValueError, match="Nothing to edit"):
        edit_user(sql_session, user)


def test_edit_user_rejects_resubmitting_the_same_card_and_rfid(sql_session: Session) -> None:
    user = _make_user(sql_session)

    with pytest.raises(ValueError, match="Nothing to edit"):
        edit_user(sql_session, user, card="ntnu123", rfid="deadbeef")


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


def test_edit_user_does_not_apply_any_change_when_the_call_fails(sql_session: Session) -> None:
    user = _make_user(sql_session)

    with pytest.raises(ValueError):
        edit_user(sql_session, user, card="ntnu456", name="Alicia")

    sql_session.expire_all()

    assert user.card == "ntnu123"
    assert user.name == "alice"


def test_edit_user_rejects_empty_name(sql_session: Session) -> None:
    user = _make_user(sql_session)

    with pytest.raises(ValueError, match="Name cannot be empty"):
        edit_user(sql_session, user, name="")

    sql_session.expire_all()

    assert user.name == "alice"


def test_edit_user_rejects_duplicate_name(sql_session: Session) -> None:
    _make_user(sql_session, "alice")
    bob = _make_user(sql_session, "bob", card="ntnu456", rfid="cafebabe")

    with pytest.raises(ValueError, match="already exists"):
        edit_user(sql_session, bob, name="alice")

    sql_session.expire_all()

    assert bob.name == "bob"


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


def test_edit_user_rejects_invalid_card(sql_session: Session) -> None:
    user = _make_user(sql_session)

    with pytest.raises(ValueError, match="invalid format"):
        edit_user(sql_session, user, card="not-a-card")

    sql_session.expire_all()

    assert user.card == "ntnu123"


def test_edit_user_rejects_invalid_rfid(sql_session: Session) -> None:
    user = _make_user(sql_session)

    with pytest.raises(ValueError, match="invalid format"):
        edit_user(sql_session, user, rfid="not-hex!")

    sql_session.expire_all()

    assert user.rfid == "deadbeef"


def test_edit_user_does_not_apply_card_change_when_rfid_is_invalid(sql_session: Session) -> None:
    user = _make_user(sql_session)

    with pytest.raises(ValueError, match="invalid format"):
        edit_user(sql_session, user, card="ntnu456", rfid="not-hex!")

    sql_session.expire_all()

    assert user.card == "ntnu123"
    assert user.rfid == "deadbeef"


def test_edit_user_rejects_uppercase_rename(sql_session: Session) -> None:
    user = _make_user(sql_session)

    with pytest.raises(ValueError, match="lowercase letters only"):
        edit_user(sql_session, user, name="Alicia")

    sql_session.expire_all()

    assert user.name == "alice"


def test_edit_user_can_rename(sql_session: Session) -> None:
    user = _make_user(sql_session, "alice")

    edit_user(sql_session, user, name="alicia")

    sql_session.expire_all()

    assert sql_session.get(User, user.id) is user
    assert user.name == "alicia"
    assert sql_session.query(User).filter_by(name="alice").first() is None


def test_edit_user_rejects_duplicate_card(sql_session: Session) -> None:
    _make_user(sql_session, "alice")
    bob = _make_user(sql_session, "bob", card="ntnu456", rfid="cafebabe")

    with pytest.raises(ValueError, match="already exists"):
        edit_user(sql_session, bob, card="NTNU123")

    sql_session.expire_all()

    assert bob.card == "ntnu456"


def test_edit_user_rejects_duplicate_rfid(sql_session: Session) -> None:
    _make_user(sql_session, "alice")
    bob = _make_user(sql_session, "bob", card="ntnu456", rfid="cafebabe")

    with pytest.raises(ValueError, match="already exists"):
        edit_user(sql_session, bob, rfid="DEADBEEF")

    sql_session.expire_all()

    assert bob.rfid == "cafebabe"


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

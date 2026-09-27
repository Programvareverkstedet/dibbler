import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from dibbler.models import User
from dibbler.queries import edit_user


def _make_user(sql_session: Session, name: str = "alice") -> User:
    user = User(name, "ntnu123", "deadbeef")
    sql_session.add(user)
    sql_session.flush()
    return user


def test_edit_user_updates_only_the_given_fields(sql_session: Session) -> None:
    user = _make_user(sql_session)

    edit_user(sql_session, user, card="ntnu456", rfid=None)

    sql_session.expire_all()

    assert user.card == "ntnu456"
    assert user.rfid is None


def test_edit_user_leaves_user_untouched_when_nothing_is_passed(sql_session: Session) -> None:
    user = _make_user(sql_session)

    edit_user(sql_session, user)

    sql_session.expire_all()

    assert user.card == "ntnu123"
    assert user.rfid == "deadbeef"


def test_edit_user_does_not_apply_any_change_when_the_call_fails(sql_session: Session) -> None:
    user = _make_user(sql_session)

    with pytest.raises(ValueError):
        edit_user(sql_session, user, card="ntnu456", name="alicia")

    sql_session.expire_all()

    assert user.card == "ntnu123"
    assert user.name == "alice"


def test_edit_user_rejects_rename_without_explicit_guard(sql_session: Session) -> None:
    user = _make_user(sql_session)

    with pytest.raises(ValueError, match="not supported"):
        edit_user(sql_session, user, name="alicia")

    sql_session.expire_all()

    assert user.name == "alice"


def test_edit_user_rejects_empty_name_even_with_guard(sql_session: Session) -> None:
    user = _make_user(sql_session)

    with pytest.raises(ValueError, match="Name cannot be empty"):
        edit_user(sql_session, user, name="", _allow_rename=True)

    sql_session.expire_all()

    assert user.name == "alice"


def test_edit_user_rejects_duplicate_name_even_with_guard(sql_session: Session) -> None:
    _make_user(sql_session, "alice")
    bob = _make_user(sql_session, "bob")

    with pytest.raises(IntegrityError):
        edit_user(sql_session, bob, name="alice", _allow_rename=True)


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


def test_edit_user_rejects_uppercase_rename_even_with_guard(sql_session: Session) -> None:
    user = _make_user(sql_session)

    with pytest.raises(ValueError, match="lowercase letters only"):
        edit_user(sql_session, user, name="Alicia", _allow_rename=True)

    sql_session.expire_all()

    assert user.name == "alice"


def test_edit_user_can_rename_with_explicit_guard(sql_session: Session) -> None:
    user = _make_user(sql_session, "alice")

    edit_user(sql_session, user, name="alicia", _allow_rename=True)

    sql_session.expire_all()

    assert sql_session.get(User, "alicia") is user
    assert sql_session.get(User, "alice") is None

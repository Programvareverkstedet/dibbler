from collections.abc import Callable

import pytest
from sqlalchemy.orm import Session

from dibbler.models import User
from dibbler.queries import (
    check_user_card_available,
    check_user_name_available,
    check_user_rfid_available,
    create_user,
)


def _make_users(sql_session: Session) -> dict[str, User]:
    return {
        "alice": create_user(sql_session, "alice", "ntnu123", "deadbeef"),
        "bob": create_user(sql_session, "bob"),
    }


@pytest.mark.parametrize(
    ("check", "value", "user"),
    [
        pytest.param(check_user_name_available, "carol", None, id="create-free-name"),
        pytest.param(check_user_card_available, "ntnu456", None, id="create-free-card"),
        pytest.param(check_user_rfid_available, "cafebabe", None, id="create-free-rfid"),

        pytest.param(check_user_name_available, "alice", "alice", id="edit-own-name"),
        pytest.param(check_user_card_available, "NTNU123", "alice", id="edit-own-card"),
        pytest.param(check_user_rfid_available, "DEADBEEF", "alice", id="edit-own-rfid"),
    ],
)  # fmt: skip
def test_passes(
    sql_session: Session,
    check: Callable[..., None],
    value: str,
    user: str | None,
) -> None:
    users = _make_users(sql_session)

    check(sql_session, value, users.get(user))


@pytest.mark.parametrize(
    ("check", "value", "user"),
    [
        pytest.param(check_user_name_available, "alice", None, id="create-taken-name"),
        pytest.param(check_user_card_available, "ntnu123", None, id="create-taken-card"),
        pytest.param(check_user_card_available, "NTNU123", None, id="create-taken-card-uppercase"),
        pytest.param(check_user_rfid_available, "deadbeef", None, id="create-taken-rfid"),
        pytest.param(check_user_rfid_available, "DEADBEEF", None, id="create-taken-rfid-uppercase"),

        pytest.param(check_user_name_available, "alice", "bob", id="edit-taken-name"),
        pytest.param(check_user_card_available, "ntnu123", "bob", id="edit-taken-card"),
        pytest.param(check_user_rfid_available, "deadbeef", "bob", id="edit-taken-rfid"),
    ],
)  # fmt: skip
def test_fails(
    sql_session: Session,
    check: Callable[..., None],
    value: str,
    user: str | None,
) -> None:
    users = _make_users(sql_session)

    with pytest.raises(ValueError, match="already exists"):
        check(sql_session, value, users.get(user))

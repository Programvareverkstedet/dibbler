import pytest
from sqlalchemy.orm import Session

from dibbler.models import User
from dibbler.queries import search_user


def _make_users(sql_session: Session) -> dict[str, User]:
    users = [
        User("alice", card="ntnu123", rfid="deadbeef"),
        User("alicia", None),
        User("bob", card="ntnu45678", rfid="cafebabe00"),
        User("azzzb", None),
        User("axb", None),
    ]
    sql_session.add_all(users)
    sql_session.flush()
    return {user.name: user for user in users}


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        pytest.param("nonexistent", set(), id="no-match"),

        pytest.param("alice", "alice", id="exact-name"),
        pytest.param("ALICE", "alice", id="exact-name-ignores-case"),
        pytest.param("ali", {"alice", "alicia"}, id="partial-name"),

        # TODO: should we maybe just disallow non-[a-z] altogether?
        pytest.param("a%b", set(), id="escapes-percent"),
        pytest.param("a_b", set(), id="escapes-underscore"),

        pytest.param("ntnu123", "alice", id="exact-card"),
        pytest.param("ntnu456", {"bob"}, id="partial-card"),

        pytest.param("deadbeef", "alice", id="exact-rfid"),
        pytest.param("babe00", {"bob"}, id="partial-rfid"),
    ],
)  # fmt: skip
def test_search_user(sql_session: Session, query: str, expected: str | set[str]) -> None:
    users = _make_users(sql_session)

    result = search_user(sql_session, query)

    if isinstance(expected, str):
        assert result is users[expected]
    else:
        assert isinstance(result, list)
        assert {user.name for user in result} == expected


def test_search_user_rejects_empty_string(sql_session: Session) -> None:
    with pytest.raises(ValueError, match="cannot be empty"):
        search_user(sql_session, "")

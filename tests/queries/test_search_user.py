import pytest
from sqlalchemy.orm import Session

from dibbler.models import User
from dibbler.queries import search_user


def _make_user(
    sql_session: Session,
    name: str,
    card: str | None = None,
    rfid: str | None = None,
) -> User:
    user = User(name, card, rfid)
    sql_session.add(user)
    sql_session.flush()
    return user


def test_search_user_matches_exact_name(sql_session: Session) -> None:
    alice = _make_user(sql_session, "alice")
    _make_user(sql_session, "alicia")

    result = search_user("alice", sql_session)

    assert result is alice


def test_search_user_matches_are_case_insensitive(sql_session: Session) -> None:
    alice = _make_user(sql_session, "alice")

    result = search_user("ALICE", sql_session)

    assert result is alice


def test_search_user_matches_exact_card(sql_session: Session) -> None:
    alice = _make_user(sql_session, "alice", card="ntnu123")

    result = search_user("ntnu123", sql_session)

    assert result is alice


def test_search_user_matches_exact_rfid(sql_session: Session) -> None:
    alice = _make_user(sql_session, "alice", rfid="deadbeef")

    result = search_user("deadbeef", sql_session)

    assert result is alice


def test_search_user_returns_partial_matches(sql_session: Session) -> None:
    alice = _make_user(sql_session, "alice")
    alicia = _make_user(sql_session, "alicia")
    _make_user(sql_session, "bob")

    result = search_user("ali", sql_session)

    assert isinstance(result, list)
    assert set(result) == {alice, alicia}


def test_search_user_returns_empty_list_for_no_match(sql_session: Session) -> None:
    _make_user(sql_session, "alice")

    result = search_user("nonexistent", sql_session)

    assert result == []


def test_search_user_partial_matches_on_card_and_rfid(sql_session: Session) -> None:
    alice = _make_user(sql_session, "alice", card="ntnu12345", rfid="deadbeef00")

    by_card = search_user("ntnu123", sql_session)
    by_rfid = search_user("beef00", sql_session)

    assert by_card == [alice]
    assert by_rfid == [alice]


def test_search_user_rejects_empty_string(sql_session: Session) -> None:
    with pytest.raises(ValueError, match="cannot be empty"):
        search_user("", sql_session)


def test_search_user_escapes_percent(sql_session: Session) -> None:
    _make_user(sql_session, "azzzb")

    result = search_user("a%b", sql_session)

    assert result == []


def test_search_user_escapes_underscore(sql_session: Session) -> None:
    _make_user(sql_session, "axb")

    result = search_user("a_b", sql_session)

    assert result == []

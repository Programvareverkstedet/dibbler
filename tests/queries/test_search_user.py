from sqlalchemy.orm import Session

from dibbler.models import User
from dibbler.queries.search_user import search_user

USER = [
    ("alice", 123),
    ("bob", 125),
    ("charlie", 126),
    ("david", 127),
    ("eve", 128),
    ("evey", 129),
    ("evy", 130),
    ("-symbol-man", 131),
    ("user_123", 132),
]


def setup_users(sql_session: Session) -> None:
    for username, rfid in USER:
        user = User(name=username, rfid=str(rfid))
        sql_session.add(user)
    sql_session.commit()


def test_search_user_exact_match(sql_session: Session) -> None:
    setup_users(sql_session)

    user = search_user("alice", sql_session)
    assert user is not None
    assert isinstance(user, User)
    assert user.name == "alice"

    user = search_user("125", sql_session)
    assert user is not None
    assert isinstance(user, User)
    assert user.name == "bob"


def test_search_user_partial_match(sql_session: Session) -> None:
    setup_users(sql_session)

    users = search_user("ev", sql_session)
    assert isinstance(users, list)
    assert len(users) == 3
    names = {user.name for user in users}
    assert names == {"eve", "evey", "evy"}

    users = search_user("user", sql_session)
    assert isinstance(users, list)
    assert len(users) == 1
    assert users[0].name == "user_123"


def test_search_user_no_match(sql_session: Session) -> None:
    setup_users(sql_session)

    result = search_user("nonexistent", sql_session)
    assert isinstance(result, list)
    assert len(result) == 0


def test_search_user_special_characters(sql_session: Session) -> None:
    setup_users(sql_session)

    user = search_user("-symbol-man", sql_session)
    assert user is not None
    assert isinstance(user, User)
    assert user.name == "-symbol-man"


def test_search_by_rfid(sql_session: Session) -> None:
    setup_users(sql_session)

    user = search_user("130", sql_session)
    assert user is not None
    assert isinstance(user, User)
    assert user.name == "evy"

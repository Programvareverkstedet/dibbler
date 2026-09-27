from sqlalchemy import or_
from sqlalchemy.orm import Session

from dibbler.models import User

_LIKE_ESCAPE_CHAR = "\\"


def search_user(
    string: str,
    sql_session: Session,
    # NOTE: search_products has 3 parameters, but this one only have 2.
    #       We need an extra parameter for polymorphic purposes.
    ignore_this_flag: None = None,
) -> User | list[User] | None:
    assert sql_session is not None

    if not string:
        raise ValueError("Search string cannot be empty.")

    string = string.lower()
    exact_match = (
        sql_session.query(User)
        .filter(or_(User.name == string, User.card == string, User.rfid == string))
        .first()
    )

    if exact_match:
        return exact_match

    escaped = (
        string.replace(_LIKE_ESCAPE_CHAR, _LIKE_ESCAPE_CHAR * 2)
        .replace("%", f"{_LIKE_ESCAPE_CHAR}%")
        .replace("_", f"{_LIKE_ESCAPE_CHAR}_")
    )

    return (
        sql_session.query(User)
        .filter(
            or_(
                User.name.ilike(f"%{escaped}%", escape=_LIKE_ESCAPE_CHAR),
                User.card.ilike(f"%{escaped}%", escape=_LIKE_ESCAPE_CHAR),
                User.rfid.ilike(f"%{escaped}%", escape=_LIKE_ESCAPE_CHAR),
            ),
        )
        .all()
    )

from sqlalchemy import or_
from sqlalchemy.orm import Session

from dibbler.models import User


def search_user(
    string: str,
    sql_session: Session,
    # NOTE: search_products has 3 parameters, but this one only have 2.
    #       We need an extra parameter for polymorphic purposes.
    ignore_this_flag: None = None,
) -> User | list[User] | None:
    assert sql_session is not None
    string = string.lower()
    exact_match = (
        sql_session.query(User)
        .filter(or_(User.name == string, User.card == string, User.rfid == string))
        .first()
    )
    if exact_match:
        return exact_match
    return (
        sql_session.query(User)
        .filter(
            or_(
                User.name.ilike(f"%{string}%"),
                User.card.ilike(f"%{string}%"),
                User.rfid.ilike(f"%{string}%"),
            ),
        )
        .all()
    )

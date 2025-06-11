from sqlalchemy import or_
from sqlalchemy.orm import Session

from dibbler.models import User


# TODO: modernize queries to use SQLAlchemy 2.0 style
def search_user(string: str, session: Session, ignorethisflag=None) -> User | list[User]:
    string = string.lower()
    exact_match = (
        session.query(User)
        .filter(or_(User.name == string, User.card == string, User.rfid == string))
        .first()
    )
    if exact_match:
        return exact_match
    user_list = (
        session.query(User)
        .filter(
            or_(
                User.name.ilike(f"%{string}%"),
                User.card.ilike(f"%{string}%"),
                User.rfid.ilike(f"%{string}%"),
            )
        )
        .all()
    )
    return user_list

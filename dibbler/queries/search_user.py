from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from dibbler.models import User


def search_user(
    string: str,
    sql_session: Session,
) -> User | list[User]:
    string = string.lower()

    exact_match = sql_session.scalars(
        select(User).where(
            or_(
                User.name == string,
                User.card == string,
                User.rfid == string,
            )
        )
    ).first()

    if exact_match:
        return exact_match

    user_list = sql_session.scalars(
        select(User).where(
            or_(
                User.name.ilike(f"%{string}%"),
                User.card.ilike(f"%{string}%"),
                User.rfid.ilike(f"%{string}%"),
            )
        )
    ).all()

    return list(user_list)

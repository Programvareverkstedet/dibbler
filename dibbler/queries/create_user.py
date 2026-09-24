from sqlalchemy.orm import Session

from dibbler.models import User


def create_user(
    sql_session: Session,
    name: str,
    card: str | None = None,
    rfid: str | None = None,
    credit: int = 0,
) -> User:
    if not name:
        raise ValueError("Name cannot be empty.")

    user = User(name, card, rfid, credit)
    sql_session.add(user)
    sql_session.flush()

    return user

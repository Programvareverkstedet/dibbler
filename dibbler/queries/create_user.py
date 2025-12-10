from sqlalchemy.orm import Session

from dibbler.models import User


def create_user(
    sql_session: Session,
    name: str,
    card: str | None,
    rfid: str | None,
) -> User:
    if not name:
        raise ValueError("Name cannot be empty.")

    # TODO: check for duplicate names, cards, rfids

    user = User(name=name, card=card, rfid=rfid)
    sql_session.add(user)
    sql_session.commit()

    return user

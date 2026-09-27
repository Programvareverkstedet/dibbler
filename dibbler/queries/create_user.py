import re

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

    if not re.fullmatch(User.name_re, name):
        raise ValueError("Name must consist of lowercase letters only.")

    if card:
        if not re.fullmatch(User.card_re, card):
            raise ValueError("Card number has an invalid format.")
        card = card.lower()

    if rfid:
        if not re.fullmatch(User.rfid_re, rfid):
            raise ValueError("RFID has an invalid format.")
        rfid = rfid.lower()

    user = User(name, card, rfid, credit)
    sql_session.add(user)
    sql_session.flush()

    return user

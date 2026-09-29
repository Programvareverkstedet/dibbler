import re
from datetime import datetime

from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from dibbler.models import User, UserLog
from dibbler.models.enums import UserLogEntryType


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

    if sql_session.scalar(select(exists().where(User.name == name))):
        raise ValueError(f'A user named "{name}" already exists.')

    if card:
        if not re.fullmatch(User.card_re, card):
            raise ValueError("Card number has an invalid format.")
        card = card.lower()

    if rfid:
        if not re.fullmatch(User.rfid_re, rfid):
            raise ValueError("RFID has an invalid format.")
        rfid = rfid.lower()

    if card and sql_session.scalar(select(exists().where(User.card == card))):
        raise ValueError(f'A user with card number "{card}" already exists.')

    if rfid and sql_session.scalar(select(exists().where(User.rfid == rfid))):
        raise ValueError(f'A user with RFID "{rfid}" already exists.')

    user = User(name, card, rfid, credit)
    sql_session.add(user)
    sql_session.flush()

    sql_session.add(
        UserLog(
            type=UserLogEntryType.CREATE,
            time=datetime.now(),
            user_id=user.id,
            name=user.name,
            card=user.card,
            rfid=user.rfid,
            credit=user.credit,
        ),
    )

    sql_session.flush()

    return user

import re
from datetime import datetime
from typing import Any

from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from dibbler.models import User, UserLog
from dibbler.models.enums import UserLogEntryType

UNSET: Any = object()


def edit_user(
    sql_session: Session,
    user: User,
    name: str | None = UNSET,
    card: str | None = UNSET,
    rfid: str | None = UNSET,
) -> User:
    if name is not UNSET:
        if not name:
            raise ValueError("Name cannot be empty.")
        if not re.fullmatch(User.name_re, name):
            raise ValueError("Name must consist of lowercase letters only.")
        if name != user.name and sql_session.scalar(select(exists().where(User.name == name))):
            raise ValueError(f'A user named "{name}" already exists.')

    if card == "":
        card = None

    if rfid == "":
        rfid = None

    if card is not UNSET and card:
        if not re.fullmatch(User.card_re, card):
            raise ValueError("Card number has an invalid format.")
        card = card.lower()
        if card != user.card and sql_session.scalar(select(exists().where(User.card == card))):
            raise ValueError(f'A user with card number "{card}" already exists.')

    if rfid is not UNSET and rfid:
        if not re.fullmatch(User.rfid_re, rfid):
            raise ValueError("RFID has an invalid format.")
        rfid = rfid.lower()
        if rfid != user.rfid and sql_session.scalar(select(exists().where(User.rfid == rfid))):
            raise ValueError(f'A user with RFID "{rfid}" already exists.')

    changed = (
        (name is not UNSET and name != user.name)
        or (card is not UNSET and card != user.card)
        or (rfid is not UNSET and rfid != user.rfid)
    )
    if not changed:
        raise ValueError("Nothing to edit.")

    if name is not UNSET:
        assert name
        user.name = name

    if card is not UNSET:
        user.card = card

    if rfid is not UNSET:
        user.rfid = rfid

    sql_session.add(
        UserLog(
            type=UserLogEntryType.EDIT,
            time=datetime.now(),
            user_id=user.id,
            name=name if name is not UNSET else None,
            card=card if card is not UNSET else None,
            card_touched=card is not UNSET,
            rfid=rfid if rfid is not UNSET else None,
            rfid_touched=rfid is not UNSET,
        ),
    )

    sql_session.flush()

    return user

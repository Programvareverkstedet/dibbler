import re
from datetime import datetime
from typing import Any

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
    _allow_rename: bool = False,
) -> User:
    if name is not UNSET:
        # TODO: Have users be identified by a primary integer id instead of their name.
        if not _allow_rename:
            raise ValueError(
                "Renaming a user is not supported atm, just complain to someone about it if you really need it.",
            )
        if not name:
            raise ValueError("Name cannot be empty.")
        if not re.fullmatch(User.name_re, name):
            raise ValueError("Name must consist of lowercase letters only.")

    if card is not UNSET and card:
        if not re.fullmatch(User.card_re, card):
            raise ValueError("Card number has an invalid format.")
        card = card.lower()

    if rfid is not UNSET and rfid:
        if not re.fullmatch(User.rfid_re, rfid):
            raise ValueError("RFID has an invalid format.")
        rfid = rfid.lower()

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
            user_id=user.name,
            name=name if name is not UNSET else None,
            card=card if card is not UNSET else None,
            card_touched=card is not UNSET,
            rfid=rfid if rfid is not UNSET else None,
            rfid_touched=rfid is not UNSET,
        ),
    )

    sql_session.flush()

    return user

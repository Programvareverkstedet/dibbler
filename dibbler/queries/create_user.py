import re
from datetime import datetime

from sqlalchemy.orm import Session

from dibbler.models import User, UserLog
from dibbler.models.enums import UserLogEntryType

from .check_user_available import (
    check_user_card_available,
    check_user_name_available,
    check_user_rfid_available,
)


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

    if len(name) > User.name_length:
        raise ValueError(f"Name must be at most {User.name_length} characters.")

    check_user_name_available(sql_session, name)

    if card:
        if not re.fullmatch(User.card_re, card):
            raise ValueError("Card number has an invalid format.")
        if len(card) > User.card_length:
            raise ValueError(f"Card number must be at most {User.card_length} characters.")
        card = card.lower()

    if rfid:
        if not re.fullmatch(User.rfid_re, rfid):
            raise ValueError("RFID has an invalid format.")
        if len(rfid) > User.rfid_length:
            raise ValueError(f"RFID must be at most {User.rfid_length} characters.")
        rfid = rfid.lower()

    if card:
        check_user_card_available(sql_session, card)

    if rfid:
        check_user_rfid_available(sql_session, rfid)

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

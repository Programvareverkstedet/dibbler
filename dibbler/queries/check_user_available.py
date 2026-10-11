from sqlalchemy import exists, select
from sqlalchemy.orm import InstrumentedAttribute, Session

from dibbler.models import User


def _is_taken(
    sql_session: Session,
    column: InstrumentedAttribute[str | None],
    value: str,
    user: User | None,
) -> bool:
    conditions = [column == value]
    if user is not None:
        conditions.append(User.id != user.id)
    return bool(sql_session.scalar(select(exists().where(*conditions))))


def check_user_name_available(
    sql_session: Session,
    name: str,
    user: User | None = None,
) -> None:
    """
    Raise a `ValueError` if a user already has this name.

    If `user` is given, they are allowed to keep their own name.
    """
    if _is_taken(sql_session, User.name, name, user):
        raise ValueError(f'A user named "{name}" already exists.')


def check_user_card_available(
    sql_session: Session,
    card: str,
    user: User | None = None,
) -> None:
    """
    Raise a `ValueError` if a user already has this card number.

    If `user` is given, they are allowed to keep their own card number.
    """
    card = card.lower()
    if _is_taken(sql_session, User.card, card, user):
        raise ValueError(f'A user with card number "{card}" already exists.')


def check_user_rfid_available(
    sql_session: Session,
    rfid: str,
    user: User | None = None,
) -> None:
    """
    Raise a `ValueError` if a user already has this RFID.

    If `user` is given, they are allowed to keep their own RFID.
    """
    rfid = rfid.lower()
    if _is_taken(sql_session, User.rfid, rfid, user):
        raise ValueError(f'A user with RFID "{rfid}" already exists.')

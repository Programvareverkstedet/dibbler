from typing import Any

from sqlalchemy.orm import Session

from dibbler.models import User

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
        user.name = name

    if card is not UNSET:
        user.card = card

    if rfid is not UNSET:
        user.rfid = rfid

    sql_session.flush()

    return user

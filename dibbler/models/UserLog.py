from __future__ import annotations

from datetime import datetime  # noqa: TC003 SQLAlchemy needs this at runtime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Integer,
    String,
    column,
    event,
    or_,
)
from sqlalchemy.orm import (
    Mapped,
    Session,
    foreign,
    mapped_column,
    relationship,
)

from ._helpers import type_field_constraints, validate_log_lifecycle
from .Base import Base
from .enums import UserLogEntryType, UserLogEntryTypeSQL
from .mixins import UidMixin
from .User import User


class UserLog(Base, UidMixin):
    __tablename__ = "user_log"
    __table_args__ = (
        *type_field_constraints(
            {
                UserLogEntryType.CREATE: {"name": True, "credit": True},
                UserLogEntryType.EDIT: {"credit": False},
                UserLogEntryType.DELETE: {
                    "name": False,
                    "card": False,
                    "rfid": False,
                    "credit": False,
                },
            },
        ),
        CheckConstraint(
            or_(
                column("type") != UserLogEntryType.EDIT.value,
                or_(
                    column("name").is_not(None),
                    column("card_touched").is_(True),
                    column("rfid_touched").is_(True),
                ),
            ),
            name="ck_edit_touches_something",
        ),
    )

    time: Mapped[datetime] = mapped_column(DateTime)
    type: Mapped[UserLogEntryType] = mapped_column(UserLogEntryTypeSQL)

    # NOTE: Technically a foreign key, but we don't enforce so we can delete users.
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    user: Mapped[User | None] = relationship(
        primaryjoin=lambda: foreign(UserLog.user_id) == User.id,
        viewonly=True,
    )

    name: Mapped[str | None] = mapped_column(String(User.name_length))
    card: Mapped[str | None] = mapped_column(String(User.card_length))
    card_touched: Mapped[bool] = mapped_column(Boolean, default=False)
    rfid: Mapped[str | None] = mapped_column(String(User.rfid_length))
    rfid_touched: Mapped[bool] = mapped_column(Boolean, default=False)
    credit: Mapped[int | None] = mapped_column(Integer)


@event.listens_for(Session, "before_flush")
def _validate_user_log_lifecycles(
    session: Session,
    _flush_context: object,
    _instances: object,
) -> None:
    validate_log_lifecycle(
        session,
        UserLog,
        UserLog.user_id,
        create_type=UserLogEntryType.CREATE,
        delete_type=UserLogEntryType.DELETE,
    )

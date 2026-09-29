from __future__ import annotations

from datetime import datetime  # noqa: TC003 SQLAlchemy needs this at runtime
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    ForeignKey,
    String,
    event,
)
from sqlalchemy.orm import (
    Mapped,
    Session,
    mapped_column,
    relationship,
)

from dibbler.lib.sql_helpers import type_field_constraints

from .Base import Base
from .enums import TransactionLogEntryType, TransactionLogEntryTypeSQL
from .mixins import UidMixin

if TYPE_CHECKING:
    from collections.abc import Callable

    from .ProductLog import ProductLog
    from .xref_tables import TransactionLogProduct, TransactionLogUser


class TransactionLog(Base, UidMixin):
    __tablename__ = "transaction_log"
    __table_args__ = (
        *type_field_constraints(
            {
                TransactionLogEntryType.BUY_PRODUCT: {"merge_ref_id": False},
                TransactionLogEntryType.ADD_PRODUCT: {"merge_ref_id": False},
                TransactionLogEntryType.ADJUST_STOCK: {"merge_ref_id": None},
                TransactionLogEntryType.TRANSFER: {"merge_ref_id": False},
                TransactionLogEntryType.ADJUST_BALANCE: {"merge_ref_id": False},
            },
        ),
    )

    time: Mapped[datetime] = mapped_column(DateTime)
    type: Mapped[TransactionLogEntryType] = mapped_column(TransactionLogEntryTypeSQL)
    description: Mapped[str | None] = mapped_column(String(50))

    products: Mapped[set[TransactionLogProduct]] = relationship(back_populates="transaction")
    users: Mapped[set[TransactionLogUser]] = relationship(back_populates="transaction")

    merge_ref_id: Mapped[int | None] = mapped_column(ForeignKey("product_log.id"))
    merge_ref: Mapped[ProductLog | None] = relationship()


_EXPECTED_COUNTS: dict[
    TransactionLogEntryType,
    tuple[tuple[int, int | None], tuple[int, int | None]],
] = {
    # min/max number of (users, products) per type
    TransactionLogEntryType.BUY_PRODUCT: ((1, None), (1, None)),
    TransactionLogEntryType.ADD_PRODUCT: ((1, None), (1, None)),
    TransactionLogEntryType.ADJUST_STOCK: ((1, 1), (1, 1)),
    TransactionLogEntryType.TRANSFER: ((2, 2), (0, 0)),
    TransactionLogEntryType.ADJUST_BALANCE: ((1, 1), (0, 0)),
}


_USER_AMOUNT_RULES: dict[
  TransactionLogEntryType,
  tuple[Callable[[int | None], bool], str],
] = {
    TransactionLogEntryType.BUY_PRODUCT: (lambda amount: bool(amount), "a non-zero amount"),
    TransactionLogEntryType.ADD_PRODUCT: (lambda amount: amount is not None, "an amount"),
    TransactionLogEntryType.ADJUST_STOCK: (lambda amount: amount is None, "no amount"),
    TransactionLogEntryType.TRANSFER: (lambda amount: bool(amount), "a non-zero amount"),
    TransactionLogEntryType.ADJUST_BALANCE: (lambda amount: bool(amount), "a non-zero amount"),
}


def _describe_minmax(minmax: tuple[int, int | None]) -> str:
    low, high = minmax
    if high is None:
        return f"at least {low}"
    if low == high:
        return f"exactly {low}"
    return f"{low} to {high}"


@event.listens_for(Session, "before_flush")
def _validate_transaction_log_entries(
    session: Session,
    _flush_context: object,
    _instances: object,
) -> None:
    for entry in (*session.new, *session.dirty):
        if not isinstance(entry, TransactionLog):
            continue

        user_minmax, product_minmax = _EXPECTED_COUNTS[entry.type]
        counts_and_minmax = [
            (len(entry.users), user_minmax),
            (len(entry.products), product_minmax),
        ]
        if not all(
            low <= count and (high is None or count <= high)
            for count, (low, high) in counts_and_minmax
        ):
            raise ValueError(
                f"A {entry.type} log entry must have {_describe_minmax(user_minmax)} users and "
                f"{_describe_minmax(product_minmax)} products, "
                f"got {len(entry.users)} users and {len(entry.products)} products.",
            )

        amount_is_valid, amount_description = _USER_AMOUNT_RULES[entry.type]
        for user in entry.users:
            if not amount_is_valid(user.amount):
                raise ValueError(
                    f"Every user in a {entry.type} log entry must have {amount_description}, "
                    f"got {user.amount}.",
                )

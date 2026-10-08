from collections import defaultdict
from collections.abc import Mapping
from enum import Enum
from typing import TYPE_CHECKING, Any

from sqlalchemy import CheckConstraint, ColumnElement, and_, column, or_, select
from sqlalchemy.orm import InstrumentedAttribute, Session

if TYPE_CHECKING:
    from datetime import datetime


def type_field_constraints(
    expected_fields: Mapping[Enum, Mapping[str, bool | None]],
    *,
    type_column: str = "type",
    name_prefix: str = "ck",
    treat_empty_as_forbidden: bool = False,
) -> list[CheckConstraint]:
    """
    Helper to create sql check constraints from a mapping of log item type to required/optional/forbidden fields.
    """

    def is_forbidden(field: str) -> ColumnElement[bool]:
        if treat_empty_as_forbidden:
            return or_(column(field).is_(None), column(field) == "")
        return column(field).is_(None)

    constraints = []
    for entry_type, fields in expected_fields.items():
        required = {field for field, state in fields.items() if state is True}
        forbidden = {field for field, state in fields.items() if state is False}
        if not required and not forbidden:
            continue
        constraints.append(
            CheckConstraint(
                or_(
                    column(type_column) != entry_type.value,
                    and_(
                        *(column(field).is_not(None) for field in required),
                        *(is_forbidden(field) for field in forbidden),
                    ),
                ),
                name=f"{name_prefix}_{entry_type.value}_fields",
            ),
        )

    return constraints


def validate_log_lifecycle(
    session: Session,
    log_class: type[Any],
    subject_id_column: InstrumentedAttribute[int],
    create_type: Enum,
    delete_type: Enum,
) -> None:
    """
    Used for `ProductLog` and `UserLog` to ensure that:

    - There are no double `CREATE` entries for the same object.
    - There are no double `DELETE` entries for the same object.
    - Any modifications to an object must be sandwiched between a `CREATE` and a `DELETE`.
    """

    # NOTE: session.new follows the order the entries were added in.
    new_entries = [entry for entry in session.new if isinstance(entry, log_class)]
    if not new_entries:
        return

    subject_ids = {getattr(entry, subject_id_column.key) for entry in new_entries}
    existing_entries = session.execute(
        select(subject_id_column, log_class.time, log_class.type)
        .where(subject_id_column.in_(subject_ids))
        .order_by(log_class.time, log_class.id),
    ).all()

    timelines: dict[int, list[tuple[datetime, int, int, Enum]]] = defaultdict(list)
    for index, (subject_id, time, entry_type) in enumerate(existing_entries):
        timelines[subject_id].append((time, 0, index, entry_type))
    for index, entry in enumerate(new_entries):
        timelines[getattr(entry, subject_id_column.key)].append((entry.time, 1, index, entry.type))

    for subject_id, timeline in timelines.items():
        has_create = False
        is_alive = False
        for time, _is_new, _index, entry_type in sorted(timeline, key=lambda item: item[:3]):
            description = f"{entry_type} entry for {subject_id_column.key}={subject_id} at {time}"
            if entry_type == create_type and is_alive:
                raise ValueError(
                    f"Cannot have a {description}, it already has a {create_type} entry.",
                )
            if entry_type != create_type and not has_create:
                raise ValueError(
                    f"Cannot have a {description}, it has no {create_type} entry before it.",
                )
            if entry_type != create_type and not is_alive:
                raise ValueError(
                    f"Cannot have a {description}, it has a {delete_type} entry before it.",
                )
            has_create = has_create or entry_type == create_type
            is_alive = entry_type != delete_type

from sqlalchemy.orm import Session

from dibbler.models import Transaction, User
from dibbler.queries.current_penalty import current_penalty

# TODO: this type of transaction should be password protected.
#       the password can be set as a string literal in the config file.


def adjust_penalty(
    sql_session: Session,
    user: User,
    new_penalty: int | None = None,
    new_penalty_multiplier: int | None = None,
    message: str | None = None,
) -> None:
    if new_penalty is None and new_penalty_multiplier is None:
        raise ValueError("At least one of new_penalty or new_penalty_multiplier must be provided")

    if new_penalty_multiplier is not None and new_penalty_multiplier < 100:
        raise ValueError("Penalty multiplier cannot be less than 100%")

    if user.id is None:
        raise ValueError("User must be persisted in the database.")

    if new_penalty is None or new_penalty_multiplier is None:
        existing_penalty, existing_penalty_multiplier = current_penalty(sql_session)
        if new_penalty is None:
            new_penalty = existing_penalty
        if new_penalty_multiplier is None:
            new_penalty_multiplier = existing_penalty_multiplier

    transaction = Transaction.adjust_penalty(
        user_id=user.id,
        penalty_threshold=new_penalty,
        penalty_multiplier_percent=new_penalty_multiplier,
        message=message,
    )

    sql_session.add(transaction)
    sql_session.commit()

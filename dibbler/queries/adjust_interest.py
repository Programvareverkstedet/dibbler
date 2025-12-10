from sqlalchemy.orm import Session

from dibbler.models import Transaction, User

# TODO: this type of transaction should be password protected.
#       the password can be set as a string literal in the config file.


def adjust_interest(
    sql_session: Session,
    user: User,
    new_interest: int,
    message: str | None = None,
) -> None:
    if new_interest < 0:
        raise ValueError("Interest rate cannot be negative")

    if user.id is None:
        raise ValueError("User must be persisted in the database.")

    transaction = Transaction.adjust_interest(
        user_id=user.id,
        interest_rate_percent=new_interest,
        message=message,
    )

    sql_session.add(transaction)
    sql_session.commit()

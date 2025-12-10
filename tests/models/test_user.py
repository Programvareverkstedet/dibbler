import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from dibbler.models import User


def insert_test_data(sql_session: Session) -> User:
    user = User("Test User")
    sql_session.add(user)
    sql_session.commit()

    return user


def test_ensure_no_duplicate_user_names(sql_session: Session) -> None:
    user = insert_test_data(sql_session)

    user2 = User(user.name)
    sql_session.add(user2)

    with pytest.raises(IntegrityError):
        sql_session.commit()

from sqlalchemy.orm import Session
from dibbler.models import Base


def main(sql_session: Session):
    if not sql_session.bind:
        raise RuntimeError("SQLAlchemy session is not bound to a database engine.")
    Base.metadata.create_all(sql_session.bind)

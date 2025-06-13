import pytest

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from dibbler.models import Base


def pytest_addoption(parser):
    parser.addoption(
        "--echo",
        action="store_true",
        help="Enable SQLAlchemy echo mode for debugging",
    )


@pytest.fixture(scope="function")
def sql_session(request):
    """Create a new SQLAlchemy session for testing."""

    echo = request.config.getoption("--echo")

    engine = create_engine(
        "sqlite:///:memory:",
        echo=echo,
    )

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    with Session(engine) as sql_session:
        yield sql_session

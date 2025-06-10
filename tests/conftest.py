import pytest

from sqlalchemy import create_engine
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
    Base.metadata.create_all(engine)
    with Session(engine) as sql_session:
        yield sql_session

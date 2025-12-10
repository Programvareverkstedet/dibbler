import logging

import pytest
import sqlparse
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from dibbler.models import Base


def pytest_addoption(parser):
    parser.addoption(
        "--echo",
        action="store_true",
        help="Enable SQLAlchemy echo mode for debugging",
    )


class SqlParseFormatter(logging.Formatter):
    def format(self, record):
        recordMessage = record.getMessage()
        if not recordMessage.startswith("[") and any(
            recordMessage.startswith(keyword)
            for keyword in [
                "SELECT",
                "INSERT",
                "UPDATE",
                "DELETE",
                "WITH",
            ]
        ):
            formatted_sql = sqlparse.format(recordMessage, reindent=True, keyword_case="upper")
            record.msg = "\n" + formatted_sql

        return super().format(record)


@pytest.fixture(scope="function")
def sql_session(request):
    """Create a new SQLAlchemy session for testing."""

    logging.basicConfig()
    logger = logging.getLogger("sqlalchemy.engine")
    handler = logging.StreamHandler()
    handler.setFormatter(SqlParseFormatter())
    logger.addHandler(handler)

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

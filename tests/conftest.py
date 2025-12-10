import logging

import pytest
import sqlparse
from sqlalchemy import create_engine, event
from sqlalchemy.exc import OperationalError
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


def pytest_configure(config):
    """Setup pretty SQL logging if --echo is enabled."""

    logger = logging.getLogger("sqlalchemy.engine")

    # TODO: it would be nice not to duplicate these logs.
    #       logging.NullHandler() does not seem to work here
    handler = logging.StreamHandler()
    handler.setFormatter(SqlParseFormatter())
    logger.addHandler(handler)

    echo = config.getoption("--echo")
    if echo:
        logger.setLevel(logging.INFO)


@pytest.fixture(scope="function")
def sql_session(request):
    """Create a new SQLAlchemy session for testing."""

    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, _connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    with Session(engine) as sql_session:
        yield sql_session


# FIXME: Declaring this hook seems to have a side effect where the database does not
#        get reset between tests.
# @pytest.hookimpl(trylast=True)
# def pytest_runtest_call(item: pytest.Item):
#     """Hook to format SQL statements in OperationalError exceptions."""
#     try:
#         item.runtest()
#     except OperationalError as e:
#         if e.statement is not None:
#             formatted_sql = sqlparse.format(e.statement, reindent=True, keyword_case="upper")
#             e.statement = "\n" + formatted_sql + "\n"
#         raise e

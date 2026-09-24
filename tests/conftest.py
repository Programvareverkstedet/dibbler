from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import pytest
import sqlparse
from sqlalchemy import create_engine, event
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from dibbler.models import Base

if TYPE_CHECKING:
    from collections.abc import Iterator

    from sqlalchemy.engine.interfaces import DBAPIConnection
    from sqlalchemy.pool import ConnectionPoolEntry


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--debug-sql",
        action="store_true",
        help="Enable SQLAlchemy 'echo' mode for debugging",
    )


class SqlParseFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
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


def pytest_configure(config: pytest.Config) -> None:
    """Setup pretty SQL logging if --debug-sql is enabled."""

    logger = logging.getLogger("sqlalchemy.engine")

    handler = logging.StreamHandler()
    handler.setFormatter(SqlParseFormatter())
    logger.addHandler(handler)

    if config.getoption("--debug-sql"):
        logger.setLevel(logging.INFO)


@pytest.fixture(scope="function")
def sql_session(request: pytest.FixtureRequest) -> Iterator[Session]:
    """Create a new SQLAlchemy session backed by an in-memory sqlite database."""

    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(
        dbapi_connection: DBAPIConnection,
        _connection_record: ConnectionPoolEntry,
    ) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    try:
        Base.metadata.create_all(engine)
        with Session(engine) as sql_session:
            yield sql_session
    finally:
        engine.dispose()


@pytest.hookimpl(wrapper=True)
def pytest_runtest_call(item: pytest.Item) -> object:
    """Hook to format SQL statements in OperationalError exceptions."""
    try:
        return (yield)
    except OperationalError as e:
        if e.statement is not None:
            formatted_sql = sqlparse.format(e.statement, reindent=True, keyword_case="upper")
            e.statement = "\n" + formatted_sql + "\n"
        raise e

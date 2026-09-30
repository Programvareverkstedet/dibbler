from __future__ import annotations

import logging
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING

import allure
import psycopg2
import pytest
import sqlparse
from psycopg2 import sql as pg_sql
from sqlalchemy import URL, Engine, create_engine, event
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
    parser.addoption(
        "--db-driver",
        action="store",
        choices=["sqlite", "postgresql"],
        default="sqlite",
    )
    parser.addoption(
        "--pg-username",
        action="store",
        default=None,
    )
    parser.addoption(
        "--pg-password",
        action="store",
        default=None,
    )
    parser.addoption(
        "--pg-admin-database",
        action="store",
        default="postgres",
    )
    parser.addoption(
        "--pg-host",
        action="store",
        default="localhost",
    )
    parser.addoption(
        "--pg-port",
        action="store",
        type=int,
        default=5432,
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

    if (
        config.getoption("--db-driver") == "postgresql"
        and config.getoption("--pg-username") is None
    ):
        raise pytest.UsageError("--pg-username is required when --db-driver=postgresql")


@dataclass(frozen=True)
class PgOptions:
    host: str
    port: int
    username: str
    password: str | None
    admin_database: str

    @classmethod
    def from_args(cls, config: pytest.Config) -> PgOptions:
        return cls(
            host=config.getoption("--pg-host"),
            port=config.getoption("--pg-port"),
            username=config.getoption("--pg-username"),
            password=config.getoption("--pg-password"),
            admin_database=config.getoption("--pg-admin-database"),
        )


@contextmanager
def _postgres_engine(pg_options: PgOptions) -> Iterator[Engine]:
    """Create a throwaway PostgreSQL database and yield a SQLAlchemy engine
    pointing at it, dropping the database again on exit."""

    db_name = f"dibbler_test_{uuid.uuid4().hex}"

    admin_conn = psycopg2.connect(
        host=pg_options.host,
        port=pg_options.port,
        user=pg_options.username,
        password=pg_options.password,
        dbname=pg_options.admin_database,
    )
    admin_conn.autocommit = True
    try:
        with admin_conn.cursor() as cursor:
            cursor.execute(pg_sql.SQL("CREATE DATABASE {}").format(pg_sql.Identifier(db_name)))

        url = URL.create(
            "postgresql+psycopg2",
            username=pg_options.username,
            password=pg_options.password,
            host=pg_options.host,
            port=pg_options.port,
            database=db_name,
        )
        engine = create_engine(url)
        try:
            yield engine
        finally:
            engine.dispose()
            with admin_conn.cursor() as cursor:
                # Forcefully terminate all connections to the database
                cursor.execute(
                    "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                    "WHERE datname = %s AND pid != pg_backend_pid()",
                    (db_name,),
                )

                cursor.execute(
                    pg_sql.SQL("DROP DATABASE IF EXISTS {}").format(pg_sql.Identifier(db_name)),
                )
    finally:
        admin_conn.close()


@contextmanager
def _sqlite_engine() -> Iterator[Engine]:
    """Yield a SQLAlchemy engine for a fresh in-memory SQLite database."""

    engine = create_engine("sqlite:///:memory:")

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(
        dbapi_connection: DBAPIConnection,
        _connection_record: ConnectionPoolEntry,
    ) -> None:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA reverse_unordered_selects=ON")
        cursor.close()

    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture(scope="session")
def _postgres_session_engine(request: pytest.FixtureRequest) -> Iterator[Engine]:
    with _postgres_engine(PgOptions.from_args(request.config)) as engine:
        Base.metadata.create_all(engine)
        yield engine


@pytest.fixture(scope="function")
def sql_session(request: pytest.FixtureRequest) -> Iterator[Session]:
    """Create a new SQLAlchemy session for testing."""

    if request.config.getoption("--db-driver") == "postgresql":
        engine = request.getfixturevalue("_postgres_session_engine")
        with engine.connect() as connection:
            transaction = connection.begin()
            with Session(
                bind=connection,
                join_transaction_mode="create_savepoint",
            ) as sql_session:
                yield sql_session
            transaction.rollback()
        return

    with _sqlite_engine() as engine:
        Base.metadata.create_all(engine)
        with Session(engine) as sql_session:
            yield sql_session


@pytest.fixture(autouse=True)
def _allure_db_driver(request: pytest.FixtureRequest) -> None:
    db_driver = request.config.getoption("--db-driver")
    allure.dynamic.label("db", db_driver)
    allure.dynamic.parameter("db", db_driver)


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

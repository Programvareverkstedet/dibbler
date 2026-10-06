import sys
from pathlib import Path
from typing import NoReturn

from sqlalchemy import Engine, inspect, select
from sqlalchemy.exc import DBAPIError, OperationalError
from sqlalchemy.orm import RelationshipProperty
from sqlalchemy.orm.clsregistry import _ModuleMarker

from dibbler.lib.helpers import file_is_submissive_and_readable
from dibbler.lib.syslog import get_syslog_logger
from dibbler.models import Base

logger = get_syslog_logger()


def _report(message: str) -> None:
    print(message, file=sys.stderr)
    logger.error(message)


def _fail(message: str) -> NoReturn:
    _report(message)
    sys.exit(1)


def check_db_health(engine: Engine, verify_table_existence: bool = False) -> None:
    dialect_name = getattr(engine.dialect, "name", "").lower()

    if "postgres" in dialect_name:
        check_postgres_ping(engine)

    elif dialect_name == "sqlite":
        check_sqlite_file(engine)

    if verify_table_existence:
        verify_tables_and_columns(engine)


def check_postgres_ping(engine: Engine) -> None:
    try:
        with engine.connect() as conn:
            result = conn.execute(select(1))
            scalar = result.scalar()
            if scalar != 1 and scalar is not None:
                _fail(f"Unexpected response from Postgres when running 'SELECT 1': {scalar!r}")
    except (OperationalError, DBAPIError) as exc:
        _fail(f"Failed to connect to Postgres database: {exc}")


def check_sqlite_file(engine: Engine) -> None:
    db_path = engine.url.database

    # Don't verify in-memory databases or empty paths
    if db_path in (None, "", ":memory:"):
        return

    db_path = db_path.removeprefix("file:").removeprefix("sqlite:")

    # Strip query parameters
    if "?" in db_path:
        db_path = db_path.split("?", 1)[0]

    path = Path(db_path)

    if not path.exists():
        _fail(f"SQLite database file does not exist: {path}")

    if not path.is_file():
        _fail(f"SQLite database path is not a file: {path}")

    if not file_is_submissive_and_readable(path):
        _fail(f"SQLite database file is not submissive and readable: {path}")

    return


def verify_tables_and_columns(engine: Engine) -> None:
    iengine = inspect(engine)
    errors = False
    tables = iengine.get_table_names()
    views = iengine.get_view_names()
    tables.extend(views)

    for _name, klass in Base.registry._class_registry.items():
        if isinstance(klass, _ModuleMarker):
            continue

        table = klass.__tablename__
        if table in tables:
            columns = [c["name"] for c in iengine.get_columns(table)]
            mapper = inspect(klass)

            for column_prop in mapper.attrs:
                if isinstance(column_prop, RelationshipProperty):
                    pass
                else:
                    for column in column_prop.columns:
                        if not column.key in columns:
                            _report(
                                f"Model '{klass}' declares column '{column.key}' which does not exist in database {engine}",
                            )
                            errors = True
        else:
            _report(
                f"Model '{klass}' declares table '{table}' which does not exist in database {engine}",
            )
            errors = True

    if errors:
        print("Have you remembered to run `dibbler create-db?", file=sys.stderr)
        sys.exit(1)

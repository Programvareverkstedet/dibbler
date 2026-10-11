import shlex
import sys
import tomllib
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import Any

from sqlalchemy.engine import URL

from dibbler.lib.helpers import file_is_submissive_and_readable
from dibbler.lib.syslog import get_syslog_logger

DEFAULT_CONFIG_PATH = Path("/etc/dibbler/dibbler.toml")

DEFAULT_POSTGRESQL_PORT = 5432
DEFAULT_POSTGRESQL_USERNAME = "dibbler"
DEFAULT_POSTGRESQL_DBNAME = "dibbler"


logger = get_syslog_logger()

config: dict[str, dict[str, Any]] = {}


class _Default(Enum):
    REQUIRED = auto()
    NO_DEFAULT = auto()


_REQUIRED = _Default.REQUIRED
_NO_DEFAULT = _Default.NO_DEFAULT


@dataclass(frozen=True)
class ConfigField:
    type: type
    default: Any = _REQUIRED


GENERAL_SCHEMA: dict[str, ConfigField] = {
    "stop_allowed": ConfigField(bool, default=False),
    "quit_allowed": ConfigField(bool, default=True),
    "show_tracebacks": ConfigField(bool, default=True),
    "pager": ConfigField(str, default="less"),
}

SQLITE_SCHEMA: dict[str, ConfigField] = {
    "path": ConfigField(str, default="test.db"),
}

POSTGRESQL_SCHEMA: dict[str, ConfigField] = {
    "host": ConfigField(str, default="localhost"),
    "port": ConfigField(int, default=DEFAULT_POSTGRESQL_PORT),
    "username": ConfigField(str, default=DEFAULT_POSTGRESQL_USERNAME),
    "dbname": ConfigField(str, default=DEFAULT_POSTGRESQL_DBNAME),
    "password": ConfigField(str, default=""),
    "password_file": ConfigField(str, default=_NO_DEFAULT),
}


def load_config(config_path: Path | None = None) -> None:
    global config
    if config_path is None:
        if not file_is_submissive_and_readable(DEFAULT_CONFIG_PATH):
            print(
                "Could not read config file, it was neither provided nor readable in default location",
                file=sys.stderr,
            )
            logger.error(
                "Could not read config file, it was neither provided nor readable at %s",
                DEFAULT_CONFIG_PATH,
            )
            sys.exit(1)
        config_path = DEFAULT_CONFIG_PATH

    try:
        with Path(config_path).open("rb") as file:
            loaded = tomllib.load(file)
    except (OSError, tomllib.TOMLDecodeError) as e:
        print(f"Could not load config file {config_path}: {e}", file=sys.stderr)
        logger.error("Could not load config file %s: %s", config_path, e)
        sys.exit(1)

    config.clear()
    config.update(loaded)

    fill_config_defaults()
    validate_config()


def _fill_section_defaults(section: dict[str, Any], schema: dict[str, ConfigField]) -> None:
    for key, field in schema.items():
        if key not in section and field.default not in (_REQUIRED, _NO_DEFAULT):
            section[key] = field.default


def fill_config_defaults() -> None:
    _fill_section_defaults(config.setdefault("general", {}), GENERAL_SCHEMA)

    database = config.setdefault("database", {})
    if database.get("type") == "sqlite":
        _fill_section_defaults(database.setdefault("sqlite", {}), SQLITE_SCHEMA)
    elif database.get("type") == "postgresql":
        _fill_section_defaults(database.setdefault("postgresql", {}), POSTGRESQL_SCHEMA)


def _validate_section(
    data: Any,
    schema: dict[str, ConfigField] | None,
    path: str,
    errors: list[str],
) -> dict[str, Any] | None:
    if not isinstance(data, dict):
        errors.append(f"Missing or invalid [{path}] section")
        return None
    if schema is None:
        return data
    for key, field in schema.items():
        if key not in data:
            if field.default is _REQUIRED:
                errors.append(f"Missing required config key: {path}.{key}")
            continue
        if not isinstance(data[key], field.type):
            errors.append(f"Config key {path}.{key} must be of type {field.type.__name__}")
    return data


def validate_config() -> None:
    errors: list[str] = []

    general = _validate_section(config.get("general"), GENERAL_SCHEMA, "general", errors)
    if general is not None and isinstance(general.get("pager"), str):
        try:
            if not shlex.split(general["pager"]):
                errors.append("Config key general.pager must not be empty")
        except ValueError as e:
            errors.append(f"Config key general.pager could not be parsed: {e}")

    database = _validate_section(config.get("database"), None, "database", errors)
    if database is not None:
        db_type = database.get("type")
        if db_type not in ("sqlite", "postgresql"):
            errors.append(
                f"Config key database.type must be 'sqlite' or 'postgresql', got {db_type!r}",
            )
        elif db_type == "sqlite":
            _validate_section(database.get("sqlite"), SQLITE_SCHEMA, "database.sqlite", errors)
        elif db_type == "postgresql":
            _validate_section(
                database.get("postgresql"),
                POSTGRESQL_SCHEMA,
                "database.postgresql",
                errors,
            )

    if errors:
        message = "Invalid configuration:\n" + "\n".join(f"  - {error}" for error in errors)
        print(message, file=sys.stderr)
        logger.error(message)
        sys.exit(1)


def config_db_string() -> URL:
    db_type = config["database"]["type"]

    if db_type == "sqlite":
        path = Path(config["database"]["sqlite"]["path"])
        return URL.create("sqlite", database=str(path.absolute()))

    postgresql = config["database"]["postgresql"]
    host = postgresql["host"]
    port = postgresql["port"]
    username = postgresql["username"]
    dbname = postgresql["dbname"]

    if "password_file" in postgresql:
        password_file = Path(postgresql["password_file"])
        try:
            with password_file.open("r") as f:
                password = f.read().strip()
        except OSError as e:
            print(f"Could not read Postgres password file: {e}", file=sys.stderr)
            logger.error("Could not read Postgres password file %s: %s", password_file, e)
            sys.exit(1)
    else:
        password = postgresql["password"]

    if host.startswith("/"):
        return URL.create(
            "postgresql+psycopg2",
            username=username,
            password=password,
            database=dbname,
            query={"host": host, "application_name": "dibbler"},
        )
    return URL.create(
        "postgresql+psycopg2",
        username=username,
        password=password,
        host=host,
        port=port,
        database=dbname,
        query={"application_name": "dibbler"},
    )

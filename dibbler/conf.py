import sys
import tomllib
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import Any

from dibbler.lib.helpers import file_is_submissive_and_readable

DEFAULT_CONFIG_PATH = Path("/etc/dibbler/dibbler.toml")

DEFAULT_POSTGRESQL_PORT = 5432
DEFAULT_POSTGRESQL_USERNAME = "dibbler"
DEFAULT_POSTGRESQL_DBNAME = "dibbler"


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
}

LIMITS_SCHEMA: dict[str, ConfigField] = {
    "low_credit_warning_limit": ConfigField(int, default=-100),
    "user_recent_transaction_limit": ConfigField(int, default=100),
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
    if config_path is not None:
        with Path(config_path).open("rb") as file:
            config = tomllib.load(file)
    elif file_is_submissive_and_readable(DEFAULT_CONFIG_PATH):
        with DEFAULT_CONFIG_PATH.open("rb") as file:
            config = tomllib.load(file)
    else:
        print(
            "Could not read config file, it was neither provided nor readable in default location",
            file=sys.stderr,
        )
        sys.exit(1)

    fill_config_defaults()
    validate_config()


def _fill_section_defaults(section: dict[str, Any], schema: dict[str, ConfigField]) -> None:
    for key, field in schema.items():
        if key not in section and field.default not in (_REQUIRED, _NO_DEFAULT):
            section[key] = field.default


def fill_config_defaults() -> None:
    _fill_section_defaults(config.setdefault("general", {}), GENERAL_SCHEMA)
    _fill_section_defaults(config.setdefault("limits", {}), LIMITS_SCHEMA)

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

    _validate_section(config.get("general"), GENERAL_SCHEMA, "general", errors)
    _validate_section(config.get("limits"), LIMITS_SCHEMA, "limits", errors)

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
        print("Invalid configuration:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        sys.exit(1)


def config_db_string() -> str:
    db_type = config["database"]["type"]

    if db_type == "sqlite":
        path = Path(config["database"]["sqlite"]["path"])
        return f"sqlite:///{path.absolute()}"

    postgresql = config["database"]["postgresql"]
    host = postgresql["host"]
    port = postgresql["port"]
    username = postgresql["username"]
    dbname = postgresql["dbname"]

    if "password_file" in postgresql:
        with Path(postgresql["password_file"]).open("r") as f:
            password = f.read().strip()
    else:
        password = postgresql["password"]

    if host.startswith("/"):
        return f"postgresql+psycopg2://{username}:{password}@/{dbname}?host={host}"
    return f"postgresql+psycopg2://{username}:{password}@{host}:{port}/{dbname}"

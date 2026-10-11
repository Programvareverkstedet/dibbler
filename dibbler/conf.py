import shlex
import tomllib
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import Any

from sqlalchemy.engine import URL

from dibbler.lib.helpers import file_is_submissive_and_readable

DEFAULT_CONFIG_PATH = Path("/etc/dibbler/dibbler.toml")

DEFAULT_POSTGRESQL_PORT = 5432
DEFAULT_POSTGRESQL_USERNAME = "dibbler"
DEFAULT_POSTGRESQL_DBNAME = "dibbler"


config: dict[str, dict[str, Any]] = {}


class ConfigError(Exception):
    pass


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


def read_config(config_path: Path | None = None) -> dict[str, dict[str, Any]]:
    if config_path is None:
        if not file_is_submissive_and_readable(DEFAULT_CONFIG_PATH):
            raise ConfigError(
                "Could not read config file, it was neither provided "
                f"nor readable at {DEFAULT_CONFIG_PATH}",
            )
        config_path = DEFAULT_CONFIG_PATH

    try:
        with Path(config_path).open("rb") as file:
            loaded = tomllib.load(file)
    except (OSError, tomllib.TOMLDecodeError) as e:
        raise ConfigError(f"Could not load config file {config_path}: {e}") from e

    fill_config_defaults(loaded)
    validate_config(loaded)
    return loaded


def replace_config(new_config: dict[str, dict[str, Any]]) -> None:
    config.clear()
    config.update(new_config)


def load_config(config_path: Path | None = None) -> None:
    replace_config(read_config(config_path))


def _fill_section_defaults(section: dict[str, Any], schema: dict[str, ConfigField]) -> None:
    for key, field in schema.items():
        if key not in section and field.default not in (_REQUIRED, _NO_DEFAULT):
            section[key] = field.default


def fill_config_defaults(cfg: dict[str, Any]) -> None:
    _fill_section_defaults(cfg.setdefault("general", {}), GENERAL_SCHEMA)

    database = cfg.setdefault("database", {})
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


def validate_config(cfg: dict[str, Any]) -> None:
    errors: list[str] = []

    general = _validate_section(cfg.get("general"), GENERAL_SCHEMA, "general", errors)
    if general is not None and isinstance(general.get("pager"), str):
        try:
            if not shlex.split(general["pager"]):
                errors.append("Config key general.pager must not be empty")
        except ValueError as e:
            errors.append(f"Config key general.pager could not be parsed: {e}")

    database = _validate_section(cfg.get("database"), None, "database", errors)
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
        raise ConfigError(
            "Invalid configuration:\n" + "\n".join(f"  - {error}" for error in errors),
        )


def config_db_string(cfg: dict[str, Any]) -> URL:
    db_type = cfg["database"]["type"]

    if db_type == "sqlite":
        path = Path(cfg["database"]["sqlite"]["path"])
        return URL.create("sqlite", database=str(path.absolute()))

    postgresql = cfg["database"]["postgresql"]
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
            raise ConfigError(f"Could not read Postgres password file {password_file}: {e}") from e
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

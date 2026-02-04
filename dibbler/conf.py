import os
import sys
import tomllib
from pathlib import Path
from typing import Any

DEFAULT_CONFIG_PATH = Path("/etc/dibbler/dibbler.toml")


def default_config_path_submissive_and_readable() -> bool:
    return DEFAULT_CONFIG_PATH.is_file() and any(
        [
            (
                DEFAULT_CONFIG_PATH.stat().st_mode & 0o400
                and DEFAULT_CONFIG_PATH.stat().st_uid == os.getuid()
            ),
            (
                DEFAULT_CONFIG_PATH.stat().st_mode & 0o040
                and DEFAULT_CONFIG_PATH.stat().st_gid == os.getgid()
            ),
            (DEFAULT_CONFIG_PATH.stat().st_mode & 0o004),
        ],
    )


config: dict[str, dict[str, Any]] = {}


def load_config(config_path: Path | None = None) -> None:
    global config
    if config_path is not None:
        with Path(config_path).open("rb") as file:
            config = tomllib.load(file)
    elif default_config_path_submissive_and_readable():
        with DEFAULT_CONFIG_PATH.open("rb") as file:
            config = tomllib.load(file)
    else:
        print(
            "Could not read config file, it was neither provided nor readable in default location",
            file=sys.stderr,
        )
        sys.exit(1)


def config_db_string() -> str:
    db_type = config["database"]["type"]

    if db_type == "sqlite":
        path = Path(config["database"]["sqlite"]["path"])
        return f"sqlite:///{path.absolute()}"

    if db_type == "postgresql":
        host = config["database"]["postgresql"]["host"]
        port = config["database"]["postgresql"].get("port", 5432)
        username = config["database"]["postgresql"].get("username", "dibbler")
        dbname = config["database"]["postgresql"].get("dbname", "dibbler")

        if "password_file" in config["database"]["postgresql"]:
            with Path(config["database"]["postgresql"]["password_file"]).open("r") as f:
                password = f.read().strip()
        elif "password" in config["database"]["postgresql"]:
            password = config["database"]["postgresql"]["password"]
        else:
            password = ""

        if host.startswith("/"):
            return f"postgresql+psycopg2://{username}:{password}@/{dbname}?host={host}"
        return f"postgresql+psycopg2://{username}:{password}@{host}:{port}/{dbname}"
    print(f"Error: unknown database type '{db_type}'")
    exit(1)

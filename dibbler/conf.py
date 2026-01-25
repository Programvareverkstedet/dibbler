from typing import Any
from pathlib import Path
import tomllib
import os
import sys

DEFAULT_CONFIG_PATH = Path('/etc/dibbler/dibbler.toml')

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
        ]
    )

config: dict[str, dict[str, Any]] = dict()

def load_config(config_path: Path | None = None):
    global config
    if config_path is not None:
        with Path(config_path).open("rb") as file:
            config = tomllib.load(file)
    elif default_config_path_submissive_and_readable():
        with DEFAULT_CONFIG_PATH.open("rb") as file:
            config = tomllib.load(file)
    else:
        print("Could not read config file, it was neither provided nor readable in default location", file=sys.stderr)
        sys.exit(1)

# This module is supposed to act as a singleton and be filled
# with config variables by cli.py
from pathlib import Path
import os

import configparser

config = configparser.ConfigParser()

DEFAULT_CONFIG_PATH = Path('/etc/dibbler/dibbler.conf')

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

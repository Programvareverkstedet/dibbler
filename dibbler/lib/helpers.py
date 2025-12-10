import os
import pwd
import signal
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any, Literal


def system_user_exists(username: str) -> bool:
    try:
        pwd.getpwnam(username)
    except KeyError:
        return False
    except UnicodeEncodeError:
        return False
    else:
        return True


def guess_data_type(string: str) -> Literal["card", "rfid", "bar_code", "username"] | None:
    if string.startswith("ntnu") and string[4:].isdigit():
        return "card"
    if string.isdigit() and len(string) == 10:
        return "rfid"
    if string.isdigit() and len(string) in [8, 13]:
        return "bar_code"
    # 	if string.isdigit() and len(string) > 5:
    # 		return 'card'
    if string.isalpha() and string.islower() and system_user_exists(string):
        return "username"
    return None


def argmax(
    d: dict[Any, Any],
    all_: bool = False,
    value: Callable[[Any], Any] | None = None,
) -> Any | list[Any] | None:
    maxarg = None
    if value is not None:
        dd = d
        d = {}
        for key in list(dd.keys()):
            d[key] = value(dd[key])
    for key in list(d.keys()):
        if maxarg is None or d[key] > d[maxarg]:
            maxarg = key
    if all_:
        return [k for k in list(d.keys()) if d[k] == d[maxarg]]
    return maxarg


def less(string: str) -> None:
    """
    Run less with string as input; wait until it finishes.
    """
    # If we don't ignore SIGINT while running the `less` process,
    # it will become a zombie when someone presses C-c.
    int_handler = signal.signal(signal.SIGINT, signal.SIG_IGN)
    env = dict(os.environ)
    env["LESSSECURE"] = "1"
    proc = subprocess.Popen("less", env=env, encoding="utf-8", stdin=subprocess.PIPE)
    proc.communicate(string)
    signal.signal(signal.SIGINT, int_handler)


def file_is_submissive_and_readable(file: Path) -> bool:
    return file.is_file() and any(
        [
            file.stat().st_mode & 0o400 and file.stat().st_uid == os.getuid(),
            file.stat().st_mode & 0o040 and file.stat().st_gid == os.getgid(),
            file.stat().st_mode & 0o004,
        ],
    )

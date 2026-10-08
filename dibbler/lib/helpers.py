import os
import pwd
from collections import Counter
from collections.abc import Callable, Hashable
from math import gcd
from pathlib import Path
from typing import Any, Literal, TypeVar

HashableT = TypeVar("HashableT", bound=Hashable)


def system_user_exists(username: str) -> bool:
    try:
        pwd.getpwnam(username)
    except KeyError:
        return False
    except UnicodeEncodeError:
        return False
    else:
        return True


def guess_data_type(string: str) -> Literal["card", "rfid", "barcode", "username"] | None:
    if string.startswith("ntnu") and string[4:].isdigit():
        return "card"
    if string.isdigit() and len(string) == 10:
        return "rfid"
    if string.isdigit() and len(string) in [8, 13]:
        return "barcode"
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


def simplify_shares(shares: list[HashableT]) -> list[HashableT]:
    """
    Reduce a list of shares to its simplest variant with the same ratio.
    Used for simplifying buyer and stock-adder shares.

    Items are kept in the order they appear.
    """
    if not shares:
        return []

    counts = Counter(shares)
    divisor = gcd(*counts.values())

    simplified = []
    remaining = {item: count // divisor for item, count in counts.items()}
    for item in shares:
        if remaining[item] > 0:
            simplified.append(item)
            remaining[item] -= 1
    return simplified


def pascal_case_to_snake_case(name: str) -> str:
    return "".join(["_" + i.lower() if i.isupper() else i for i in name]).lstrip("_")


def file_is_submissive_and_readable(file: Path) -> bool:
    return file.is_file() and any(
        [
            file.stat().st_mode & 0o400 and file.stat().st_uid == os.getuid(),
            file.stat().st_mode & 0o040 and file.stat().st_gid == os.getgid(),
            file.stat().st_mode & 0o004,
        ],
    )

import os
import pwd
import signal
import subprocess
from collections.abc import Callable
from typing import Any, Literal

from sqlalchemy import and_, not_, or_
from sqlalchemy.orm import Session

from ..models import Product, User


def search_user(
    string: str,
    sql_session: Session,
    # NOTE: search_products has 3 parameters, but this one only have 2.
    #       We need an extra parameter for polymorphic purposes.
    ignore_this_flag: None = None,
) -> User | list[User] | None:
    assert sql_session is not None
    string = string.lower()
    exact_match = (
        sql_session.query(User)
        .filter(or_(User.name == string, User.card == string, User.rfid == string))
        .first()
    )
    if exact_match:
        return exact_match
    return (
        sql_session.query(User)
        .filter(
            or_(
                User.name.ilike(f"%{string}%"),
                User.card.ilike(f"%{string}%"),
                User.rfid.ilike(f"%{string}%"),
            ),
        )
        .all()
    )


def search_product(
    string: str,
    sql_session: Session,
    find_hidden_products: bool = True,
) -> Product | list[Product] | None:
    assert sql_session is not None
    if find_hidden_products:
        exact_match = (
            sql_session.query(Product)
            .filter(or_(Product.bar_code == string, Product.name == string))
            .first()
        )
    else:
        exact_match = (
            sql_session.query(Product)
            .filter(
                or_(
                    Product.bar_code == string,
                    and_(
                        Product.name == string,
                        not_(Product.hidden),
                    ),
                ),
            )
            .first()
        )
    if exact_match:
        return exact_match
    if find_hidden_products:
        product_list = (
            sql_session.query(Product)
            .filter(
                or_(
                    Product.bar_code.ilike(f"%{string}%"),
                    Product.name.ilike(f"%{string}%"),
                ),
            )
            .all()
        )
    else:
        product_list = (
            sql_session.query(Product)
            .filter(
                or_(
                    Product.bar_code.ilike(f"%{string}%"),
                    and_(
                        Product.name.ilike(f"%{string}%"),
                        not_(Product.hidden),
                    ),
                ),
            )
            .all()
        )
    return product_list


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

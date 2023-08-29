import pwd
import subprocess
import os
import signal

from sqlalchemy import or_, and_

from ..models import User, Product


def search_user(string, session, ignorethisflag=None):
    string = string.lower()
    exact_match = (
        session.query(User)
        .filter(or_(User.name == string, User.card == string, User.rfid == string))
        .first()
    )
    if exact_match:
        return exact_match
    user_list = (
        session.query(User)
        .filter(
            or_(
                User.name.ilike(f"%{string}%"),
                User.card.ilike(f"%{string}%"),
                User.rfid.ilike(f"%{string}%"),
            )
        )
        .all()
    )
    return user_list


def search_product(string, session, find_hidden_products=True):
    if find_hidden_products:
        exact_match = (
            session.query(Product)
            .filter(or_(Product.bar_code == string, Product.name == string))
            .first()
        )
    else:
        exact_match = (
            session.query(Product)
            .filter(
                or_(
                    Product.bar_code == string,
                    and_(Product.name == string, Product.hidden == False),
                )
            )
            .first()
        )
    if exact_match:
        return exact_match
    if find_hidden_products:
        product_list = (
            session.query(Product)
            .filter(
                or_(
                    Product.bar_code.ilike(f"%{string}%"),
                    Product.name.ilike(f"%{string}%"),
                )
            )
            .all()
        )
    else:
        product_list = (
            session.query(Product)
            .filter(
                or_(
                    Product.bar_code.ilike(f"%{string}%"),
                    and_(Product.name.ilike(f"%{string}%"), Product.hidden == False),
                )
            )
            .all()
        )
    return product_list


def system_user_exists(username):
    try:
        pwd.getpwnam(username)
    except KeyError:
        return False
    except UnicodeEncodeError:
        return False
    else:
        return True


def guess_data_type(string):
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


def argmax(d, all=False, value=None):
    maxarg = None
    maxargs = []
    if value != None:
        dd = d
        d = {}
        for key in list(dd.keys()):
            d[key] = value(dd[key])
    for key in list(d.keys()):
        if maxarg == None or d[key] > d[maxarg]:
            maxarg = key
    if all:
        return [k for k in list(d.keys()) if d[k] == d[maxarg]]
    return maxarg


def less(string):
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

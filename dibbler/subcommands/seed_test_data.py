import json
from dibbler.db import session as create_session

from pathlib import Path

from dibbler.models.Product import Product

from dibbler.models.User import User

JSON_FILE = Path(__file__).parent.parent.parent / "mock_data.json"


def clear_db(session):
    session.query(Product).delete()
    session.query(User).delete()
    session.commit()


def main():
    session = create_session()
    clear_db(session)
    product_items = []
    user_items = []

    with open(JSON_FILE) as f:
        json_obj = json.load(f)

        for product in json_obj["products"]:
            product_item = Product(
                bar_code=product["bar_code"],
                name=product["name"],
                price=product["price"],
                stock=product["stock"],
            )
            product_items.append(product_item)

        for user in json_obj["users"]:
            user_item = User(
                name=user["name"],
                card=user["card"],
                rfid=user["rfid"],
                credit=user["credit"],
            )
            user_items.append(user_item)

        session.add_all(product_items)
        session.add_all(user_items)
        session.commit()

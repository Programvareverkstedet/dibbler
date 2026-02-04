import json
from pathlib import Path

from sqlalchemy.orm import Session

from dibbler.models.Product import Product
from dibbler.models.User import User

JSON_FILE = Path(__file__).parent.parent.parent / "mock_data.json"


def clear_db(sql_session: Session) -> None:
    sql_session.query(Product).delete()
    sql_session.query(User).delete()
    sql_session.commit()


def main(sql_session: Session) -> None:
    clear_db(sql_session)
    product_items = []
    user_items = []

    with Path.open(JSON_FILE) as f:
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

        sql_session.add_all(product_items)
        sql_session.add_all(user_items)
        sql_session.commit()

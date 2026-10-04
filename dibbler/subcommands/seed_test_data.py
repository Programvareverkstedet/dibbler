from sqlalchemy.orm import Session

from dibbler.models import Base
from dibbler.queries import create_product, create_user

MOCK_PRODUCTS = [
    {"bar_code": "3707412130983", "name": "Cola 0.33L", "price": 13, "stock": 48},
    {"bar_code": "1974798302392", "name": "Pepsi 0.5L", "price": 22, "stock": 36},
    {"bar_code": "1293289192038", "name": "Pakke med kjeks", "price": 30, "stock": 20},
    {"bar_code": "7000000000010", "name": "PVV T-skjorte", "price": 150, "stock": 15},
]

MOCK_USERS = [
    {"name": "alice", "card": "12345678", "rfid": "a1b2c3d4e5", "credit": 500},
    {"name": "bob", "card": "23456789", "rfid": None, "credit": -50},
    {"name": "borek", "card": None, "rfid": "deadbeef12", "credit": 100},
    {"name": "kjartan", "card": "ntnu123456", "rfid": "f0912382a9", "credit": 250},
]


def clear_db(sql_session: Session) -> None:
    for table in reversed(Base.metadata.sorted_tables):
        sql_session.execute(table.delete())
    sql_session.commit()


def main(sql_session: Session) -> None:
    clear_db(sql_session)

    users = [
        create_user(sql_session, **user)  # ty: ignore[invalid-argument-type]
        for user in MOCK_USERS
    ]

    for product in MOCK_PRODUCTS:
        create_product(sql_session, **product, user=users[0])  # ty: ignore[invalid-argument-type]

    sql_session.commit()

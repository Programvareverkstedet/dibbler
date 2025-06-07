from sqlalchemy.orm import Session

# from dibbler.db import Session
from dibbler.models import User


def main(sql_session: Session):
  # Let's find all users with a negative credit
    slabbedasker = sql_session.query(User).filter(User.credit < 0).all()

    for slubbert in slabbedasker:
        print(f"{slubbert.name}, {slubbert.credit}")

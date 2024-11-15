import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from dibbler.conf import config

engine = create_engine(
    os.environ.get("DIBBLER_DATABASE_URL")
    or config.get("database", "url")
)
Session = sessionmaker(bind=engine)

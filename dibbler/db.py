from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from dibbler.conf import config

if (url := config.get("database", "url")) is not None:
  database_url = url

elif (url_file := config.get("database", "url_file")) is not None:
  with Path(url_file).open() as file:
    database_url = file.read().strip()

engine = create_engine(database_url)
Session = sessionmaker(bind=engine)

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from dibbler.conf import config

engine = create_engine(config.get("database", "url"))
Session = sessionmaker(bind=engine)

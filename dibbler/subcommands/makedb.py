#!/usr/bin/python

from sqlalchemy.engine import Engine

from dibbler.models import Base


def main(engine: Engine) -> None:
    Base.metadata.create_all(engine)

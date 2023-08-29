#!/usr/bin/python
from dibbler.models import Base
from dibbler.db import engine

def main():
  Base.metadata.create_all(engine)

if __name__ == "__main__":
  main()
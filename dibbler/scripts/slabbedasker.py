#!/usr/bin/python

from dibbler.models.db import *

def main():
  # Start an SQL session
  session=Session()
  # Let's find all users with a negative credit
  slabbedasker=session.query(User).filter(User.credit<0).all()

  for slubbert in slabbedasker:
    print(f"{slubbert.name}, {slubbert.credit}")

if __name__ == '__main__':
  main()
#!/usr/bin/python
from db import *
# Start an SQL session
session=Session()
# Let's find all users with a negative credit
slabbedasker=session.query(User).filter(User.credit<0).all()

for slubbert in slabbedasker:
	print "%s, %s" % (slubbert.name, slubbert.credit)

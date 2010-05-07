from db import *
from sqlalchemy import or_

def retrieve_user(string, session):
	first = session.query(User).filter(or_(User.name==string, User.card==string)).first()
	if first:
		print "Found user "+first.name
		return first
	else:
		list = session.query(User).filter(or_(User.name.like('%'+string+'%'),User.card.like('%'+string+'%'))).all()
		if len(list) == 0:
			print "No users found matching your search"
			return None
		if len(list) == 1:
			print "Found one user: "+list[0].name
			if confirm():
				return list[0]
			else:
				return None
		else:
			print "Found "+str(len(list))+" users:"
			return select_from_list(list)
			

def confirm():
	while True:
		input = raw_input("Confirm? (y/n)\n")
		if input in ["y","yes"]:
			return True
		elif input in ["n","no"]:
			return False
		else:
			print "Nonsense!"

def select_from_list(list):
	while True:
		for i in range(len(list)):
			print i+1, " ) ", list[i].name
		choice = raw_input("Select user :\n")
		if choice in [str(x+1) for x in range(len(list))]:
			return list[int(choice)-1]
		else:
			return None

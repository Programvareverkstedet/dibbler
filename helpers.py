from db import *
from sqlalchemy import or_

def search_user(string, session):
	exact_match = session.query(User).filter(or_(User.name==string, User.card==string)).first()
	if exact_match:
		return exact_match
	user_list = session.query(User).filter(or_(User.name.ilike('%'+string+'%'),
						   User.card.ilike('%'+string+'%'))).all()
	return user_list

def search_product(string, session):
	exact_match = session.query(Product)\
		      .filter(or_(Product.bar_code==string,
				  Product.name==string)).first()
	if exact_match:
		return exact_match
	product_list = session.query(Product)\
		       .filter(or_(Product.bar_code.ilike('%'+string+'%'),
				   Product.name.ilike('%'+string+'%'))).all()
	return product_list

def guess_data_type(string):
	if string.startswith('NTNU'):
		return 'card'
	if string.isdigit():
		return 'bar_code'
	if string.isalpha() and string.islower():
		return 'username'
	return 'product_name'


def retrieve_user(string, session):
#	first = session.query(User).filter(or_(User.name==string, User.card==string)).first()
	search = search_user(string,session)
	if isinstance(search,User):
		print "Found user "+search.name
		return search
	else:
		if len(search) == 0:
			print "No users found matching your search"
			return None
		if len(search) == 1:
			print "Found one user: "+list[0].name
			if confirm():
				return list[0]
			else:
				return None
		else:
			print "Found "+str(len(search))+" users:"
			return select_from_list(search)
			

def confirm(prompt='Confirm? (y/n) '):
	while True:
		input = raw_input(prompt)
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

def argmax(d, all=False, value=None):
	maxarg = None
	maxargs = []
	if value != None:
		dd = d
		d = {}
		for key in dd.keys():
			d[key] = value(dd[key])
	for key in d.keys():
		if maxarg == None or d[key] > d[maxarg]:
			maxarg = key
	if all:
		return filter(lambda k: d[k] == d[maxarg], d.keys())
	return maxarg

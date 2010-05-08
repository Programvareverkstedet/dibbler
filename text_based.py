import sqlalchemy
import re
from helpers import *

exit_commands = ['exit', 'abort', 'quit']

class ExitMenu(Exception):
	pass

class Menu():
	def __init__(self, name, items=[], prompt='> ',
		     return_index=True, exit_msg=None):
		self.name = name
		self.items = items
		self.prompt = prompt
		self.return_index = return_index
		self.exit_msg = exit_msg

	def at_exit(self):
		if self.exit_msg:
			print self.exit_msg

	def item_is_submenu(self, i):
		return isinstance(self.items[i], Menu)

	def item_name(self, i):
		if self.item_is_submenu(i):
			return self.items[i].name
		elif isinstance(self.items[i], tuple):
			return self.items[i][1]
		else:
			return str(self.items[i])

	def item_value(self, i):
		if isinstance(self.items[i], tuple):
			return self.items[i][0]
		if self.return_index:
			return i
		return self.items[i]

	def input_str(self, prompt=None, regex=None):
		if regex != None:
			while True:
				result = self.input_str(prompt)
				if re.match(regex+'$', result):
					return result
				else:
					print 'Value must match regular expression "%s"' % regex
		if prompt == None:
			prompt = self.prompt
		try:
			result = raw_input(prompt)
		except EOFError:
			print 'quit'
			raise ExitMenu()
		if result in exit_commands:
			raise ExitMenu()
		return result

	def input_int(self, prompt=None, allowed_range=(None,None)):
		if prompt == None:
			prompt = self.prompt
		while True:
			result = self.input_str(prompt)
			try:
				value = int(result)
				if ((allowed_range[0] and value < allowed_range[0]) or
				    (allowed_range[1] and value > allowed_range[1])):
					if allowed_range[0] and allowed_range[1]:
						print 'Value must be in range [%d,%d]' % allowed_range
					elif allowed_range[0]:
						print 'Value must be at least %d' % allowed_range[0]
					else:
						print 'Value must be at most %d' % allowed_range[1]
				else:
					return value
			except ValueError:
				print 'Please enter an integer'

	def input_user(self, prompt=None):
		user = None
		while user == None:
			user = retrieve_user(self.input_str(prompt),
					     self.session)
		return user

	def input_product(self, prompt=None):
		product = None
		while product == None:
			product = retrieve_product(self.input_str(prompt),
						   self.session)
		return product

	def input_thing(self, prompt=None, permitted_things=('user','product'),
			empty_input_permitted=False):
		result = None
		while result == None:
			search_str = self.input_str(prompt)
			if search_str == '' and empty_input_permitted:
				return None
			result = self.search_for_thing(search_str, permitted_things)
		return result

	def search_for_thing(self, search_str, permitted_things=('user','product')):
		search_fun = {'user': search_user,
			      'product': search_product}
		results = {}
		result_values = {}
		for thing in permitted_things:
			results[thing] = search_fun[thing](search_str, self.session)
			result_values[thing] = self.search_result_value(results[thing])
		selected_thing = argmax(result_values)
		return search_ui2(search_str, results[selected_thing],
				  selected_thing, self.session)

	def search_result_value(self, result):
		if result == None:
			return 0
		if not isinstance(result, list):
			return 3
		if len(result) == 0:
			return 0
		if len(result) == 1:
			return 2
		return 1

	def print_header(self):
		print
		print '[%s]' % self.name

	def pause(self):
		self.input_str('.')

	def execute(self):
		try:
			return self._execute()
		except ExitMenu:
			self.at_exit()
			return None

	def _execute(self):
		while True:
			self.print_header()
			if len(self.items)==0:
				print '(empty menu)'
				self.pause()
				return None
			for i in range(len(self.items)):
				print '%d ) %s' % (i+1, self.item_name(i))
			item_i = self.input_int(self.prompt, (1,len(self.items)))-1
			if self.item_is_submenu(item_i):
				self.items[item_i].execute()
			else:
				return self.item_value(item_i)

class Selector(Menu):
	def print_header(self):
		print self.name


class ChargeMenu(Menu):
	def __init__(self):
		self.name = "Add credits to a user account"

	def execute(self):
		self.session = Session()
		amount = self.input_int('Amount to be added> ')
		user = self.input_user('To user>')
		t = Transaction(user, -amount, 'Add '+str(amount)+' to user '+user.name)
		t.perform_transaction()
		self.session.add(t)
		self.session.commit()
		print 'Added %d kr to user %s\'s account' % (amount, user.name)
		print 'User %s\'s credit is now %d kr' % (user,user.credit)
		self.session.close()
		self.pause()

class TransferMenu(Menu):
	def __init__(self):
		Menu.__init__(self, 'Transfer credit between users')

	def _execute(self):
		self.print_header()
		self.session = Session()
		amount = self.input_int('Transfer amount> ')
		user1 = self.input_user('From user> ')
		user2 = self.input_user('To user> ')
		t1 = Transaction(user1, amount,
				 'transfer to '+user2.name)
		t2 = Transaction(user2, -amount,
				 'transfer from '+user1.name)
		t1.perform_transaction()
		t2.perform_transaction()
		self.session.add(t1)
		self.session.add(t2)
		self.session.commit()
		print 'Transfered %d kr from %s to %s' % (amount, user1, user2)
		print 'User %s\'s credit is now %d kr' % (user1, user1.credit)
		print 'User %s\'s credit is now %d kr' % (user2, user2.credit)
		self.session.close()
		self.pause()


class AddUserMenu(Menu):
	def __init__(self):
		Menu.__init__(self, 'Add user')

	def _execute(self):
		self.print_header()
		self.session = Session()
		username = self.input_str('User name> ', regex=User.name_re)
		cardnum = self.input_str('Card number> ', regex=User.card_re)
		user = User(username, cardnum)
		self.session.add(user)
		try:
			self.session.commit()
			print 'User %s stored' % username
		except sqlalchemy.exc.IntegrityError, e:
			print 'Could not store user %s: %s' % (username,e)
		self.session.close()
		self.pause()


class EditUserMenu(Menu):
	def __init__(self):
		Menu.__init__(self, 'Edit user')

	def _execute(self):
		self.print_header()
		self.session = Session()
		user = self.input_user('User> ')
		user.card = self.input_str('Card number (currently "%s")> ' % user.card,
					   regex=User.card_re)
		self.session.commit()
		print 'User %s stored' % user.name
		self.session.close()
		self.pause()


class AddProductMenu(Menu):
	def __init__(self):
		Menu.__init__(self, 'Add product')

	def _execute(self):
		self.session = Session()
		self.print_header()
		bar_code = self.input_int('Bar code> ')
		name = self.input_str('Name> ', regex=r".+")
		price = self.input_int('Price> ', (1,None))
		product = Product(bar_code, name, price)
		self.session.add(product)
		try:
			self.session.commit()
			print 'Product %s stored' % name
		except sqlalchemy.exc.IntegrityError, e:
			print 'Could not store product %s: %s' % (name,e)
		self.session.close()
		self.pause()


class EditProductMenu(Menu):
	def __init__(self):
		Menu.__init__(self, 'Edit product')

	def _execute(self):
		self.print_header()
		self.session = Session()
		product = self.input_product('Product> ')
		while True:
			selector = Selector('Do what with %s?' % product.name,
					    items=[('name', 'Edit name'),
						   ('price', 'Edit price (currently %d)' % product.price),
						   ('store', 'Store')])
			what = selector.execute()
			if what == 'name':
				product.name = self.input_str('Name> ')
			elif what == 'price':
				product.price = self.input_int('Price> ')
			elif what == 'store':
				self.session.commit()
				print 'Product %s stored' % product.name
				self.session.close()
				self.pause()
				return


class ShowUserMenu(Menu):
	def __init__(self):
		Menu.__init__(self, 'Show user')

	def _execute(self):
		self.session = Session()
		self.print_header()
		user = self.input_user('User name or card number> ')
		print 'User name: %s' % user.name
		print 'Card number: %s' % user.card
		print 'Credit: %s' % user.credit
		self.print_transactions(user)
		self.pause()

	def print_transactions(self, user):
		if len(user.transactions) == 0:
			print 'No transactions'
			return
		print 'Transactions:'
		for t in user.transactions:
			string = ' * %s: %s %d kr, ' % \
			    (t.time.strftime('%Y-%m-%d %H:%M'),
			     {True:'in', False:'out'}[t.amount<0],
			     abs(t.amount))
			if t.purchase:
				string += 'purchase ('
				string += ', '.join(map(lambda e: e.product.name,
							t.purchase.entries))
				string += ')'
			else:
				string += t.description
			print string
		

class BuyMenu(Menu):
	def __init__(self):
		Menu.__init__(self, 'Buy')

	def _execute(self):
		self.print_header()
		self.session = Session()
		self.purchase = Purchase()
		while True:
			self.print_purchase()
			print {(False,False): 'Enter user or product identification',
			       (False,True): 'Enter user identification or more products',
			       (True,False): 'Enter product identification or more users',
			       (True,True): 'Enter more products or users, or an empty line to confirm'
			       }[(len(self.purchase.transactions) > 0,
				  len(self.purchase.entries) > 0)]
			thing = self.input_thing(empty_input_permitted=True)
			if thing == None:
				if not self.complete_input():
					if confirm('Not enough information entered.  Abort purchase? (y/n) '):
						return False
					continue
				break
			if isinstance(thing, User):
				Transaction(thing, purchase=self.purchase)
			elif isinstance(thing, Product):
				PurchaseEntry(self.purchase, thing, 1)

		self.purchase.perform_purchase()

		self.session.add(self.purchase)
		self.session.commit()

		print 'Purchase stored.'
		self.print_purchase()
		for t in self.purchase.transactions:
			print 'User %s\'s credit is now %d kr' % (t.user.name, t.user.credit)
		self.session.close()
		self.pause()
		return True
		
	def complete_input(self):
		return self.purchase.is_complete()
			
	def format_purchase(self):
		self.purchase.set_price()
		transactions = self.purchase.transactions
		entries = self.purchase.entries
		if len(transactions) == 0 and len(entries) == 0:
			return None
		string = 'Purchase:'
		string += '\n buyers: '
		if len(transactions) == 0:
			string += '(empty)'
		else:
			string += ', '.join(map(lambda t: t.user.name, transactions))
		string += '\n products: '
		if len(entries) == 0:
			string += '(empty)'
		else:
			string += ', '.join(map(lambda e: '%s (%d kr)'%(e.product.name, e.product.price),
						entries))
		if len(transactions) > 1:
			string += '\n price per person: %d kr' % self.purchase.price_per_transaction()
		string += '\n total price: %d kr' % self.purchase.price
		return string

	def print_purchase(self):
		info = self.format_purchase()
		if info != None:
			print info


class AdjustCreditMenu(Menu): # reimplements ChargeMenu; these should be combined to one
	def __init__(self):
		Menu.__init__(self, 'Adjust credit')

	def _execute(self):
		self.print_header()
		self.session = Session()
		user = self.input_user('User> ')
		print 'User %s\'s credit is %d kr' % (user.name, user.credit)
		amount = self.input_int('Add amount> ')
		description = self.input_str('Log message> ')
		if description == '':
			description = 'manually adjusted credit'
		transaction = Transaction(user, -amount, description)
		transaction.perform_transaction()
		self.session.add(transaction)
		self.session.commit()
		print 'User %s\'s credit is now %d kr' % (user.name, user.credit)
		self.session.close()
		self.pause()


class ProductListMenu(Menu):
	def __init__(self):
		Menu.__init__(self, 'Product list')

	def _execute(self):
		self.print_header()
		session = Session()
		product_list = session.query(Product).all()
		line_format = '%-20s %6s %-15s'
		print line_format % ('name', 'price', 'bar code')
		print '-------------------------------------------'
		for p in product_list:
			print line_format % (p.name, p.price, p.bar_code)
		self.pause()

class AddProductMenu(Menu):
	def __init__(self):
		Menu.__init__(self, 'Add product')
	
	def _execute(self):
		name = self.input_str('Product name> ')
		bar_code = self.input_int('Bar code> ')
		price = self.input_int('Price> ')
		product = Product(bar_code,name,price)
		session = Session()
		session.add(product)
		session.commit()
		session.close()
		print 'Added product %s, price %d, bar code %d' % (name,price,bar_code)
		self.pause()


#class MainMenu():
#	def __init__(self):
#		self.menu_list = [Menu("Buy"),ChargeMenu(), Menu("Add User"), Menu("Add Product")]

#	def execute(self):
#		while 1:
#			print "Main Menu: \nWhat do you want to do? \n"
#			for i in range(len(self.menu_list)):
#				print i+1," ) ",self.menu_list[i].name
#			result = raw_input('\nEnter a number corresponding to your action, or "exit" to exit \n')
#			if result in ["1","2","3","4"]:
#				self.menu_list[int(result)-1].execute()	
#			elif result in ["quit", "exit", "abort"]:
#				print "OK, quitting"
#				break
#			else:
#				print "This does not make sense"


def dwim_search(string, session):
	typ = guess_data_type(string)
	if typ == None:
		print 'This does not make sense'
		return
	retriever = {'card': retrieve_user,
		     'username': retrieve_user,
		     'bar_code': retrieve_product,
		     'product_name': retrieve_product}
	value_type = {'card': 'user',
		      'username': 'user',
		      'bar_code': 'product',
		      'product_name': 'product'}
	value = retriever[typ](string, session)
# 	if value == None:
# 		print 'Input "%s" interpreted as %s; no matching %s found.' \
# 		      % (string, typ, value_type[typ])
	return (value_type[typ], value)

def search_ui(search_fun, search_str, thing, session):
	result = search_fun(search_str, session)
	return search_ui2(search_str, result, thing, session)

def search_ui2(search_str, result, thing, session):
	if not isinstance(result, list):
		return result
	if len(result) == 0:
		print 'No %ss matching "%s"' % (thing, search_str)
		return None
	if len(result) == 1:
		msg = 'One %s matching "%s": %s.  Use this? (y/n) ' %\
		      (thing, search_str, result[0])
		if confirm(msg):
			return result[0]
		return None
	selector = Selector('%d %ss matching "%s":' % (len(result), thing, search_str),
			    items=result,
			    return_index=False)
	return selector.execute()

def retrieve_user(search_str, session):
	return search_ui(search_user, search_str, 'user', session)
def retrieve_product(search_str, session):
	return search_ui(search_product, search_str, 'product', session)


#main = MainMenu()
main = Menu('Dibbler main menu',
	    items=[BuyMenu(), ProductListMenu(), ShowUserMenu(),
		   AdjustCreditMenu(), ChargeMenu(), TransferMenu(),
		   Menu('Add/edit',
			items=[AddUserMenu(), EditUserMenu(),
			       AddProductMenu(), EditProductMenu()])
		   ],
	    exit_msg='happy happy joy joy')
main.execute()



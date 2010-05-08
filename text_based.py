from helpers import *

exit_commands = ['exit', 'abort', 'quit']

class ExitMenu(Exception):
	pass

class Menu():
	def __init__(self, name, items=[], prompt='> ', exit_msg=None):
		self.name = name
		self.items = items
		self.prompt = prompt
		self.exit_msg = exit_msg

	def at_exit(self):
		if self.exit_msg:
			print self.exit_msg

	def item_is_submenu(self, i):
		return isinstance(self.items[i], Menu)

	def item_name(self, i):
		if self.item_is_submenu(i):
			return self.items[i].name
		else:
			return str(self.items[i])

	def input_str(self, prompt=None):
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
				return item_i

class Selector(Menu):
	def print_header(self):
		print self.name

	def _execute(self):
		result = Menu._execute(self)
		if result != None:
			return self.items[result]
		return None

class ChargeMenu(Menu):
	def __init__(self):
		self.name = "Add Credits to a User Account"

	def execute(self):
		self.session = Session()
		while 1:
			abort = False
			while 1:
				user_string = raw_input('\nEnter the user name or card number of the account you wish to add credits to, or type "exit" to exit:\n')
				if user_string in ['exit', 'abort', 'quit']:
					abort = True
					break
				else:
					user = retrieve_user(user_string,self.session)
					if user:
						break
			if abort:
				break
			while 1:
				print '\nHow much do you wish to charge?\n'
				amount_string = raw_input('Enter an amount, or type "exit" to exit:\n')
	
				if amount_string in ['exit', 'abort', 'quit']:
					abort = True
					break
				try:
					amount = int(amount_string)
					break
				except:
					print "Please enter an integer"
			if abort:
				break
			else:
				user.credit += amount
#				self.session.add(user)
				self.session.commit()
				self.session.close()
				break

class ShowUserMenu(Menu):
	def __init__(self):
		Menu.__init__(self, 'Show user')

	def _execute(self):
		self.print_header()
		user = None
		while user == None:
			search_str = self.input_str('User name or card number> ')
			user = search_ui(search_user, search_str, 'user', Session())
		print 'User name: %s' % user.name
		print 'Card number: %s' % user.card
		print 'Credit: %s' % user.credit
		self.pause()


class BuyMenu(Menu):
	def __init__(self):
		Menu.__init__(self, 'Buy')

	def _execute(self):
		self.print_header()
		session = Session()
		user = None
		products = []
		while True:
			self.print_partial_purchase(user, products)
			print {(False,False): 'Enter user or product identification',
			       (False,True): 'Enter user identification or more products',
			       (True,False): 'Enter product identification',
			       (True,True): 'Enter more products, or an empty line to confirm'
			       }[(user != None, len(products) > 0)]
			string = self.input_str()
			if string == '':
				if user == None or len(products) == 0:
					if confirm('Not enough information entered.  Abort purchase? (y/n) '):
						return False
					continue
				break
			(value_type,value) = dwim_search(string, session)
			if value != None:
				if value_type == 'user':
					user = value
				elif value_type == 'product':
					products.append(value)
		print 'OK purchase'
		print self.format_partial_purchase(user, products)
		# TODO build Purchase object and commit
		self.pause()
		
			
	def format_partial_purchase(self, user, products):
		if user == None and len(products) == 0:
			return
		strings = []
		if user != None:
			strings.append(' user: ' + user.name)
		if len(products) > 0:
			strings.append(' products: ' + ', '.join(map(lambda p: p.name, products)))
		return '\n'.join(strings)

	def print_partial_purchase(self, user, products):
		info = self.format_partial_purchase(user, products)
		if info != None:
			print 'Your purchase:\n' + info


class ProductListMenu(Menu):
	def __init__(self):
		Menu.__init__(self, 'Product list')

	def _execute(self):
		self.print_header()
		session = Session()
		product_list = session.query(Product).all()
		line_format = '%-20s %6s %-15s'
		print line_format % ('name', 'price', 'bar code')
		for p in product_list:
			print line_format % (p.name, p.price, p.bar_code)
		self.pause()


class MainMenu():
	def __init__(self):
		self.menu_list = [Menu("Buy"),ChargeMenu(), Menu("Add User"), Menu("Add Product")]

	def execute(self):
		while 1:
			print "Main Menu: \nWhat do you want to do? \n"
			for i in range(len(self.menu_list)):
				print i+1," ) ",self.menu_list[i].name
			result = raw_input('\nEnter a number corresponding to your action, or "exit" to exit \n')
			if result in ["1","2","3","4"]:
				self.menu_list[int(result)-1].execute()	
			elif result in ["quit", "exit", "abort"]:
				print "OK, quitting"
				break
			else:
				print "This does not make sense"


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
			    prompt='select> ')
	return selector.execute()

def retrieve_user(search_str, session):
	return search_ui(search_user, search_str, 'user', session)
def retrieve_product(search_str, session):
	return search_ui(search_product, search_str, 'product', session)


#main = MainMenu()
main = Menu('Dibbler main menu',
	    items=[BuyMenu(), ChargeMenu(), Menu('Add user'), Menu('Add product'),
		   ShowUserMenu(), ProductListMenu()],
	    exit_msg='happy happy joy joy')
main.execute()



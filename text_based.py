#!/usr/bin/python

import sqlalchemy
import re
import sys
import os
import traceback
import signal
import readline
from helpers import *

exit_commands = ['exit', 'abort', 'quit', 'bye', 'eat flaming death']
help_commands = ['help', '?']
context_commands = ['what', '??']
local_help_commands = ['help!', '???']
restart_commands = ['restart']

class ExitMenu(Exception):
	pass

class Menu():
	def __init__(self, name, items=[], prompt='> ',
		     return_index=True,
		     exit_msg=None, exit_confirm_msg=None, exit_disallowed_msg=None,
		     help_text=None, uses_db=False):
		self.name = name
		self.items = items
		self.prompt = prompt
		self.return_index = return_index
		self.exit_msg = exit_msg
		self.exit_confirm_msg = exit_confirm_msg
		self.exit_disallowed_msg = exit_disallowed_msg
		self.help_text = help_text
		self.context = None
		self.header_format = '[%s]'
		self.uses_db = uses_db

	def exit_menu(self):
		if self.exit_disallowed_msg != None:
			print self.exit_disallowed_msg
			return
		if self.exit_confirm_msg != None:
			if not self.confirm(self.exit_confirm_msg, default=True):
				return
		raise ExitMenu()

	def at_exit(self):
		if self.exit_msg:
			print self.exit_msg

	def set_context(self, string, display=True):
		self.context = string
		if self.context != None and display:
			print self.context

	def add_to_context(self, string):
		self.context += string

	def printc(self, string):
		print string
		if self.context == None:
			self.context = string
		else:
			self.context += '\n' + string

	def show_context(self):
		print self.header_format % self.name
		if self.context != None:
			print self.context

	def item_is_submenu(self, i):
		return isinstance(self.items[i], Menu)

	def item_name(self, i):
		if self.item_is_submenu(i):
			return self.items[i].name
		elif isinstance(self.items[i], tuple):
			return self.items[i][1]
		else:
			return self.items[i]

	def item_value(self, i):
		if isinstance(self.items[i], tuple):
			return self.items[i][0]
		if self.return_index:
			return i
		return self.items[i]

	def input_str(self, prompt=None, regex=None, length_range=(None,None),
		      empty_string_is_none=False):
		if regex != None:
			while True:
				result = self.input_str(prompt, length_range=length_range,
							empty_string_is_none=empty_string_is_none)
				if result == None or re.match(regex+'$', result):
					return result
				else:
					print 'Value must match regular expression "%s"' % regex
		if length_range != (None,None):
			while True:
				result = self.input_str(prompt, empty_string_is_none=empty_string_is_none)
				if result == None:
					length = 0
				else:
					length = len(result)
				if ((length_range[0] and length < length_range[0]) or
				    (length_range[1] and length > length_range[1])):
					if length_range[0] and length_range[1]:
						print 'Value must have length in range [%d,%d]' % length_range
					elif allowed_range[0]:
						print 'Value must have length at least %d' % length_range[0]
					else:
						print 'Value must have length at most %d' % length_range[1]
				else:
					return result
		if prompt == None:
			prompt = self.prompt
		while True:
			try:
				result = unicode(raw_input(safe_str(prompt)),
						 conf.input_encoding)
			except EOFError:
				print 'quit'
				self.exit_menu()
				continue
			if result in exit_commands:
				self.exit_menu()
				continue
			if result in help_commands:
				self.general_help()
				continue
			if result in local_help_commands:
				self.local_help()
				continue
			if result in context_commands:
				self.show_context()
				continue
			if result in restart_commands:
				if self.confirm('Restart Dibbler?'):
					restart()
				continue
			if empty_string_is_none and result == '':
				return None
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
			user = self.retrieve_user(self.input_str(prompt))
		return user

	def retrieve_user(self, search_str):
		return self.search_ui(search_user, search_str, 'user')

	def input_product(self, prompt=None):
		product = None
		while product == None:
			product = self.retrieve_product(self.input_str(prompt))
		return product

	def retrieve_product(self, search_str):
		return self.search_ui(search_product, search_str, 'product')

	def input_thing(self, prompt=None, permitted_things=('user','product'),
			add_nonexisting=(), empty_input_permitted=False):
		result = None
		while result == None:
			search_str = self.input_str(prompt)
			if search_str == '' and empty_input_permitted:
				return None
			result = self.search_for_thing(search_str, permitted_things, add_nonexisting)
		return result

	def search_for_thing(self, search_str, permitted_things=('user','product'),
			     add_nonexisting=()):
		search_fun = {'user': search_user,
			      'product': search_product}
		results = {}
		result_values = {}
		for thing in permitted_things:
			results[thing] = search_fun[thing](search_str, self.session)
			result_values[thing] = self.search_result_value(results[thing])
		selected_thing = argmax(result_values)
		if results[selected_thing] == []:
			thing_for_type = {'card': 'user', 'username': 'user',
					  'bar_code': 'product'}
			type_guess = guess_data_type(search_str)
			if type_guess != None and thing_for_type[type_guess] in add_nonexisting:
				return self.search_add(search_str)
			print 'No match found for "%s".' % search_str
			return None
		return self.search_ui2(search_str, results[selected_thing], selected_thing)

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

	def search_add(self, string):
		type_guess = guess_data_type(string)
		if type_guess == 'username':
			print '"%s" looks like a username, but no such user exists.' % string
			if self.confirm('Create user %s?' % string):
				user = User(string, None)
				self.session.add(user)
				return user
			return None
		if type_guess == 'card':
			selector = Selector('"%s" looks like a card number, but no user with that card number exists.' % string,
					    [('create', 'Create user with card number %s' % string),
					     ('set', 'Set card number of an existing user to %s' % string)])
			selection = selector.execute()
			if selection == 'create':
				username = self.input_str('Username for new user (should be same as PVV username)> ',
							  User.name_re, (1,10))
				user = User(username, string)
				self.session.add(user)
				return user
			if selection == 'set':
				user = self.input_user('User to set card number for> ')
				old_card = user.card
				user.card = string
				print 'Card number of %s set to %s (was %s)' % (user.name, string, old_card)
				return user
			return None
		if type_guess == 'bar_code':
			print '"%s" looks like the bar code for a product, but no such product exists.' % string
			return None


	def search_ui(self, search_fun, search_str, thing):
		result = search_fun(search_str, self.session)
		return self.search_ui2(search_str, result, thing)

	def search_ui2(self, search_str, result, thing):
		if not isinstance(result, list):
			return result
		if len(result) == 0:
			print 'No %ss matching "%s"' % (thing, search_str)
			return None
		if len(result) == 1:
			msg = 'One %s matching "%s": %s.  Use this?' %\
			      (thing, search_str, unicode(result[0]))
			if self.confirm(msg, default=True):
				return result[0]
			return None
		limit = 9
		if len(result) > limit:
			select_header = '%d %ss matching "%s"; showing first %d' % \
			    (len(result), thing, search_str, limit)
			select_items = result[:limit]
		else:
			select_header = '%d %ss matching "%s"' % \
			    (len(result), thing, search_str)
			select_items = result
		selector = Selector(select_header, items=select_items,
				    return_index=False)
		return selector.execute()



	def confirm(self, prompt, default=None):
		return ConfirmMenu(prompt, default).execute()

	def print_header(self):
		print
		print self.header_format % self.name

	def pause(self):
		self.input_str('.')

	def general_help(self):
		print '''
DIBBLER HELP

The following commands are recognized (almost) everywhere:

 help, ?          -- display this help
 what, ??         -- redisplay the current context
 help!, ???       -- display context-specific help (if any)
 exit, quit, etc. -- exit from the current menu

When prompted for a user, you can type (parts of) the user name or
card number.  When prompted for a product, you can type (parts of) the
product name or barcode.
'''

	def local_help(self):
		if self.help_text == None:
			print 'no help here'
		else:
			print
			print 'Help for %s:' % (self.header_format%self.name)
			print self.help_text

	def execute(self):
		self.set_context(None)
		try:
			if self.uses_db:
				self.session = Session()
			else:
				self.session = None
			return self._execute()
		except ExitMenu:
			self.at_exit()
			return None
		finally:
			if self.session != None:
				self.session.close()
				self.session = None

	def _execute(self):
		while True:
			self.print_header()
			self.set_context(None)
			if len(self.items)==0:
				self.printc('(empty menu)')
				self.pause()
				return None
			for i in range(len(self.items)):
				self.printc('%d ) %s' % (i+1, self.item_name(i)))
			item_i = self.input_int(self.prompt, (1,len(self.items)))-1
			if self.item_is_submenu(item_i):
				self.items[item_i].execute()
			else:
				return self.item_value(item_i)


class Selector(Menu):
	def __init__(self, name, items=[], prompt='select> ',
		     return_index=True,
		     exit_msg=None, exit_confirm_msg=None,
		     help_text=None):
		Menu.__init__(self, name, items, prompt, return_index, exit_msg)
		self.header_format = '%s'

	def print_header(self):
		print self.header_format % self.name

	def local_help(self):
		if self.help_text == None:
			print 'This is a selection menu.  Enter one of the listed numbers, or'
			print '\'exit\' to go out and do something else.'
		else:
			print
			print 'Help for selector (%s):' % self.name
			print self.help_text


class ConfirmMenu(Menu):
	def __init__(self, prompt='confirm?', default=None):
		Menu.__init__(self, 'question', prompt=prompt,
			      exit_disallowed_msg='Please answer yes or no')
		self.default=default

	def _execute(self):
		options = {True: '[y]/n', False: 'y/[n]', None: 'y/n'}[self.default]
		while True:
			result = self.input_str('%s (%s) ' % (self.prompt, options))
			result = result.lower()
			if result in ['y','yes']:
				return True
			if result in ['n','no']:
				return False
			if self.default != None and result == '':
				return self.default
			print 'Please answer yes or no'



# class ChargeMenu(Menu):
# 	def __init__(self):
# 		self.name = "Add credits to a user account"

# 	def execute(self):
# 		self.session = Session()
# 		amount = self.input_int('Amount to be added> ')
# 		user = self.input_user('To user>')
# 		t = Transaction(user, -amount, 'Add '+str(amount)+' to user '+user.name)
# 		t.perform_transaction()
# 		self.session.add(t)
# 		self.session.commit()
# 		print 'Added %d kr to user %s\'s account' % (amount, user.name)
# 		print 'User %s\'s credit is now %d kr' % (user,user.credit)
# 		self.session.close()
# 		self.pause()

class TransferMenu(Menu):
	def __init__(self):
		Menu.__init__(self, 'Transfer credit between users',
			      uses_db=True)

	def _execute(self):
		self.print_header()
		amount = self.input_int('Transfer amount> ', (1,100000))
		self.set_context('Transfering %d kr' % amount, display=False)
		user1 = self.input_user('From user> ')
		self.add_to_context(' from ' + user1.name)
		user2 = self.input_user('To user> ')
		self.add_to_context(' to ' + user2.name)

		t1 = Transaction(user1, amount,
				 'transfer to '+user2.name)
		t2 = Transaction(user2, -amount,
				 'transfer from '+user1.name)
		t1.perform_transaction()
		t2.perform_transaction()
		self.session.add(t1)
		self.session.add(t2)
		try:
			self.session.commit()
			print 'Transfered %d kr from %s to %s' % (amount, user1, user2)
			print 'User %s\'s credit is now %d kr' % (user1, user1.credit)
			print 'User %s\'s credit is now %d kr' % (user2, user2.credit)
		except sqlalchemy.exc.SQLAlchemyError, e:
			print 'Could not perform transfer: %s' % e
		self.pause()


class AddUserMenu(Menu):
	def __init__(self):
		Menu.__init__(self, 'Add user', uses_db=True)

	def _execute(self):
		self.print_header()
		username = self.input_str('Username (should be same as PVV username)> ', User.name_re, (1,10))
		cardnum = self.input_str('Card number (optional)> ', User.card_re, (0,10))
		user = User(username, cardnum)
		self.session.add(user)
		try:
			self.session.commit()
			print 'User %s stored' % username
		except sqlalchemy.exc.IntegrityError, e:
			print 'Could not store user %s: %s' % (username,e)
		self.pause()


class EditUserMenu(Menu):
	def __init__(self):
		Menu.__init__(self, 'Edit user', uses_db=True)
		self.help_text = '''
The only editable part of a user is its card number.

First select an existing user, then enter a new card number for that
user (write an empty line to remove the card number).
'''

	def _execute(self):
		self.print_header()
		user = self.input_user('User> ')
		self.printc('Editing user %s' % user.name)
		card_str = '"%s"' % user.card
		if user.card == None:
			card_str = 'empty'
		user.card = self.input_str('Card number (currently %s)> ' % card_str,
					   User.card_re, (0,10),
					   empty_string_is_none=True)
		try:
			self.session.commit()
			print 'User %s stored' % user.name
		except sqlalchemy.exc.SQLAlchemyError, e:
			print 'Could not store user %s: %s' % (user.name,e)
		self.pause()


class AddProductMenu(Menu):
	def __init__(self):
		Menu.__init__(self, 'Add product', uses_db=True)

	def _execute(self):
		self.print_header()
		bar_code = self.input_str('Bar code> ', Product.bar_code_re, (8,13))
		name = self.input_str('Name> ', Product.name_re, (1,30))
		price = self.input_int('Price> ', (1,100000))
		product = Product(bar_code, name, price)
		self.session.add(product)
		try:
			self.session.commit()
			print 'Product %s stored' % name
		except sqlalchemy.exc.SQLAlchemyError, e:
			print 'Could not store product %s: %s' % (name,e)
		self.pause()


class EditProductMenu(Menu):
	def __init__(self):
		Menu.__init__(self, 'Edit product', uses_db=True)

	def _execute(self):
		self.print_header()
		product = self.input_product('Product> ')
		self.printc('Editing product %s' % product.name)
		while True:
			selector = Selector('Do what with %s?' % product.name,
					    items=[('name', 'Edit name'),
						   ('price', 'Edit price (currently %d)' % product.price),
						   ('store', 'Store')])
			what = selector.execute()
			if what == 'name':
				product.name = self.input_str('Name> ', Product.name_re, (1,30))
			elif what == 'price':
				product.price = self.input_int('Price> ', (1,100000))
			elif what == 'store':
				try:
					self.session.commit()
					print 'Product %s stored' % product.name
				except sqlalchemy.exc.SQLAlchemyError, e:
					print 'Could not store product %s: %s' % (product.name, e)					
				self.pause()
				return
			elif what == None:
				print 'Edit aborted'
				return
			else:
				print 'What what?'


class ShowUserMenu(Menu):
	def __init__(self):
		Menu.__init__(self, 'Show user', uses_db=True)

	def _execute(self):
		self.print_header()
		user = self.input_user('User name or card number> ')
		print 'User name: %s' % user.name
		print 'Card number: %s' % user.card
		print 'Credit: %s kr' % user.credit
		self.print_transactions(user)
		self.pause()

	def print_transactions(self, user):
		limit = 10
		num_trans = len(user.transactions)
		if num_trans == 0:
			print 'No transactions'
			return
		if num_trans <= limit:
			print 'Transactions (%d):' % num_trans
		else:
			print 'Transactions (%d, showing only last %d):' % (num_trans,limit)
		for t in user.transactions[-limit:]:
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
		

class UserListMenu(Menu):
	def __init__(self):
		Menu.__init__(self, 'User list', uses_db=True)

	def _execute(self):
		self.print_header()
		user_list = self.session.query(User).all()
		total_credit = self.session.query(sqlalchemy.func.sum(User.credit)).first()[0]

		line_format = '%-12s | %6s'
		hline = '---------------------'
		print line_format % ('username', 'credit')
		print hline
		for user in user_list:
			print line_format % (user.name, user.credit)
		print hline
		print line_format % ('total credit', total_credit)
		self.pause()


class BuyMenu(Menu):
	def __init__(self):
		Menu.__init__(self, 'Buy', uses_db=True)
		self.help_text = '''
Each purchase may contain one or more products and one or more buyers.

Enter products (by name or bar code) and buyers (by name or bar code)
in any order.  The information gathered so far is displayed after each
addition, and you can type 'what' at any time to redisplay it.

When finished, write an empty line to confirm the purchase.
'''

	def _execute(self):
		self.print_header()
		self.purchase = Purchase()
		self.exit_confirm_msg=None
		while True:
			self.print_purchase()
			self.printc({(False,False): 'Enter user or product identification',
				     (False,True): 'Enter user identification or more products',
				     (True,False): 'Enter product identification or more users',
				     (True,True): 'Enter more products or users, or an empty line to confirm'
				     }[(len(self.purchase.transactions) > 0,
					len(self.purchase.entries) > 0)])
			thing = self.input_thing(add_nonexisting=('user',),
						 empty_input_permitted=True)
			if thing == None:
				if not self.complete_input():
					if self.confirm('Not enough information entered.  Abort purchase?',
							default=True):
						return False
					continue
				break
			else:
				# once we get something in the
				# purchase, we want to protect the
				# user from accidentally killing it
				self.exit_confirm_msg='Abort purchase?'
			if isinstance(thing, User):
				Transaction(thing, purchase=self.purchase)
			elif isinstance(thing, Product):
				PurchaseEntry(self.purchase, thing, 1)

		self.purchase.perform_purchase()
		self.session.add(self.purchase)
		try:
			self.session.commit()
		except sqlalchemy.exc.SQLAlchemyError, e:
			print 'Could not store purchase: %s' % e
		else:
			print 'Purchase stored.'
			self.print_purchase()
			for t in self.purchase.transactions:
				print 'User %s\'s credit is now %d kr' % (t.user.name, t.user.credit)
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
			string += ', '.join(map(lambda t: t.user.name,
						transactions))
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
			self.set_context(info)


class AdjustCreditMenu(Menu): # reimplements ChargeMenu; these should be combined to one
	def __init__(self):
		Menu.__init__(self, 'Adjust credit', uses_db=True)

	def _execute(self):
		self.print_header()
		user = self.input_user('User> ')
		print 'User %s\'s credit is %d kr' % (user.name, user.credit)
		self.set_context('Adjusting credit for user %s' % user.name, display=False)
		amount = self.input_int('Add amount> ', (-100000,100000))
		description = self.input_str('Log message> ', length_range=(0,50))
		if description == '':
			description = 'manually adjusted credit'
		transaction = Transaction(user, -amount, description)
		transaction.perform_transaction()
		self.session.add(transaction)
		try:
			self.session.commit()
			print 'User %s\'s credit is now %d kr' % (user.name, user.credit)
		except sqlalchemy.exc.SQLAlchemyError, e:
			print 'Could not store transaction: %s' % e
		self.pause()


class ProductListMenu(Menu):
	def __init__(self):
		Menu.__init__(self, 'Product list', uses_db=True)

	def _execute(self):
		self.print_header()
		product_list = self.session.query(Product).all()
		line_format = '%-30s | %6s | %-15s'
		print line_format % ('name', 'price', 'bar code')
		print '---------------------------------------------------------'
		for p in product_list:
			print line_format % (p.name, p.price, p.bar_code)
		self.pause()


# def dwim_search(string, session):
# 	typ = guess_data_type(string)
# 	if typ == None:
# 		print 'This does not make sense'
# 		return
# 	retriever = {'card': retrieve_user,
# 		     'username': retrieve_user,
# 		     'bar_code': retrieve_product,
# 		     'product_name': retrieve_product}
# 	value_type = {'card': 'user',
# 		      'username': 'user',
# 		      'bar_code': 'product',
# 		      'product_name': 'product'}
# 	value = retriever[typ](string, session)
# # 	if value == None:
# # 		print 'Input "%s" interpreted as %s; no matching %s found.' \
# # 		      % (string, typ, value_type[typ])
# 	return (value_type[typ], value)


def restart():
	# Does not work if the script is not executable, or if it was
	# started by searching $PATH.
	os.execv(sys.argv[0], sys.argv)


if not conf.stop_allowed:
	signal.signal(signal.SIGTSTP, signal.SIG_IGN)
main = Menu('Dibbler main menu',
	    items=[BuyMenu(), ProductListMenu(), ShowUserMenu(), UserListMenu(),
		   AdjustCreditMenu(), TransferMenu(),
		   Menu('Add/edit',
			items=[AddUserMenu(), EditUserMenu(),
			       AddProductMenu(), EditProductMenu()])
		   ],
	    exit_msg='happy happy joy joy',
	    exit_confirm_msg='Really quit Dibbler?')
if not conf.quit_allowed:
	main.exit_disallowed_msg = 'You can check out any time you like, but you can never leave.'
while True:
	try:
		main.execute()
	except KeyboardInterrupt:
		print
		print 'Interrupted.'
	except:
		print 'Something went wrong.'
		print '%s: %s' % sys.exc_info()[0:2]
		if conf.show_tracebacks:
			traceback.print_tb(sys.exc_info()[2])
	else:
		break
	print 'Restarting main menu.'

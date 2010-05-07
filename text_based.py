from helpers import *

class Menu():
	def __init__(self, name):
		self.name = name

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

main = MainMenu()
main.execute()



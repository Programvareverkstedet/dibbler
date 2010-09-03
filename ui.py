import curses
#from copy import deepcopy
#import curses.panel
import curses.textpad
#import time
import curses.ascii
from db import *


def cycle(list, index, up):
	if index <= 0 and up:
		return len(list)-1
	elif up:
		return index - 1
	elif index >= len(list)-1:
		return 0
	else:
		return index + 1

class MainMenu():
	def __init__(self, screen):
		self.screen = screen
		curses.curs_set(0)							# hide the cursor
		self.size = screen.getmaxyx()						# get screen size
		self.choices = [SubMenu("Purchase"), ChargeMenu(self.screen), SubMenu("View Transactions")]
		self.selected = 0

		self.execute()

	def execute(self):
		while 1:
			self.screen.clear()
			self.screen.border()
			for i in range(len(self.choices)):
				if i == self.selected:
					self.screen.addstr(i+1,1, str(i+1) + ") " + self.choices[i].text, curses.A_REVERSE)
				else:	
					self.screen.addstr(i+1,1, str(i+1) + ") " + self.choices[i].text)
			self.screen.refresh()
			c = self.screen.getch()
			if c == ord('q') or c == 27:
				break
			elif c == 10:				#return key
				self.choices[self.selected].execute()
			elif c == curses.KEY_UP:
				self.selected = cycle(self.choices, self.selected, True)
			elif c == curses.KEY_DOWN:
				self.selected = cycle(self.choices, self.selected, False)
			elif c >= 49 and c <= 48+len(self.choices): #number key
				self.choices[c-49].execute()

class SubMenu():
	def __init__(self, text):
		self.text = text


class ChargeMenu(SubMenu):
	def __init__(self, screen):
		self.text = "Charge"
		self.screen = screen
#		self.size = self.screen.getmaxyx()
#		self.marked = 0
#		self.textbox = False
#		self.textpad = False
#		self.textwindow = False
#		self.edit_area = False
#		self.search_text = ""
#		self.session = False

	def execute(self):
		self.make_windows()
		self.resultview = Selectable(self.resultwindow)

		# Initialize the variables

		self.marked = 0
		self.search_text = ""
		self.amount = ""
#		curses.curs_set(1)
		self.screen.move(2,2)
		self.screen.leaveok(1)
		self.session = Session()
		while 1:
			self.draw()
			c = self.screen.getch()
			if c == 27:
				break
			elif c == 9:
				self.switch_cursor()
			elif c == curses.KEY_RESIZE:
				self.resize()
			elif self.marked == 0:
				self.textpad_edit(c)
				self.textwindow.cursyncup()
			elif self.marked == 1:
#				self.amountpad.do_command(curses.ascii.SOH)
#				for char in self.amount:
#					self.amountpad.do_command(ord(char))
#				self.amountpad.do_command(curses.KEY_LEFT)
				self.amountpad_edit(c)
				self.amountwindow.cursyncup()
				self.check_calculation()
			elif self.marked == 2:
				self.resultview.do_command(c)
				self.check_calculation()
		self.session.close()

	def check_calculation(self):
		if self.amount and self.resultview.list:
			self.set_calculation()	
		else:
			self.calculation.clear()



	def draw(self):
#		if self.marked == 0:
#			(y,x) = self.textwindow.getyx()
#			y += 1
#			x += 1
#		else:
#		(y,x) = self.screen.getyx()
		self.screen.clear()
		self.screen.border()
		self.textwindow.border()
		self.amountwindow.border()
		if self.marked == 0:
			self.textwindow.addstr(0,1, "[Username or card number]",curses.A_REVERSE)
			self.amountwindow.addstr(0,1,"[Amount to be transferred]")
		elif self.marked == 1:
			self.textwindow.addstr(0,1, "[Username or card number]")
			self.amountwindow.addstr(0,1,"[Amount to be transferred]",curses.A_REVERSE)
		else:
			self.textwindow.addstr(0,1, "[Username or card number]")
			self.amountwindow.addstr(0,1,"[Amount to be transferred]")
		self.resultview.draw()
		self.textwindow.addstr(1,1,self.search_text)
		self.amountwindow.addstr(1,1,self.amount)
		self.calculation.draw()
#		curses.curs_set(1)
#		self.screen.move(y,x)
#		curses.setsyx(y,x)
#		self.textwindow.move(y-2,x-2)
		self.screen.refresh()

	def make_windows(self):
		self.size = self.screen.getmaxyx()
		self.textwindow = self.screen.subwin(3,self.size[1]/2-1,1,1)
		self.amountwindow = self.screen.subwin(3,self.size[1]/2-1,1,self.size[1]/2)
		self.edit_area = self.textwindow.subwin(1,self.size[1]/2-3,2,2)
		self.amount_area = self.amountwindow.subwin(1,self.size[1]/2-3,2,self.size[1]/2+1)
		self.resultwindow = self.screen.subwin(self.size[0]-5,self.size[1]/2-1,4,1)
		self.textpad = curses.textpad.Textbox(self.edit_area)
		self.textpad.stripspaces = True
		self.amountpad = curses.textpad.Textbox(self.amount_area)
		self.amountpad.stripspaces = True
		self.calcwindow = self.screen.subwin(self.size[0]-8,self.size[1]/2-1,4,self.size[1]/2)
		self.calculation = Calculation(self.calcwindow)

	def resize(self):
		self.make_windows()
		self.resultview.window = self.resultwindow
		self.calculation.window = self.calcwindow

	def switch_cursor(self):
		if self.marked == 4:
#			curses.curs_set(1)
			self.screen.move(2,1+len(self.search_text))
			self.marked = 0
#			self.textpad.do_command(curses.ascii.SOH)
		elif self.marked == 0:
			self.marked += 1
			self.screen.move(2,self.size[1]/2+2)
		else:
			curses.curs_set(0)
			self.marked += 1
			
	def textpad_edit(self, ch):
		self.textpad.do_command(ch)
		self.search_text = self.textpad.gather().strip()
		self.resultview.set_list(self.session.query(User).filter(or_(User.user.like(unicode('%'+self.search_text+'%')),User.id.like('%'+self.search_text+'%'))).all())
#		self.resultview.draw()
#		self.resultwindow.refresh()

	def amountpad_edit(self,ch):
		if ch >= 48 and ch <= 57:
			self.amountpad.do_command(ch)
		elif ch <= 31 or ch > 255:
			self.amountpad.do_command(ch)
		else:
			pass
		self.amount = self.amountpad.gather().strip()

	def set_calculation(self):
		self.calculation.set_numbers([self.resultview.list[self.resultview.selected].credit, int(self.amount)])

class Selectable():
	def __init__(self, window, list = [], selected = 0):
		self.list=list
		self.window = window
		self.selected = selected
#		self.attribute = attribute

	def draw(self):
		self.window.border()
		for i in range(len(self.list)):
			if i == self.selected:
				self.window.addstr(i+1,1,self.list[i].user,curses.A_REVERSE)
			else:	
				self.window.addstr(i+1,1,self.list[i].user)
		self.window.addstr(0,1,"[Search results]")

	def do_command(self,c):
		if c == curses.KEY_UP:
			self.selected = cycle(self.list, self.selected, True)
		if c == curses.KEY_DOWN:
			self.selected = cycle(self.list, self.selected, False)

	def set_list(self,list):
		if len(list)-1 < self.selected:
			self.selected = len(list)-1
			self.list = list
		else:
			self.list = list

class Calculation():
	def __init__(self, window):
		self.window = window
		self.numbers = []
		self.size = self.window.getmaxyx()

	def draw(self):
		self.window.clear()
		self.window.border()
		self.length = len(self.numbers)
		if self.length > 0:
			if self.size[0] >= self.length:
				for i in range(self.length-1):
					self.window.addstr((self.size[0]-self.length)/2+i,(self.size[1]+4-len(str(abs(self.numbers[i]))))/2,str(abs(self.numbers[i])))
					if i > 0:
						if self.numbers[i] >= 0:
							self.window.addstr((self.size[0]-self.length)/2+i,(self.size[1]-8)/2,'+')
						else:
							self.window.addstr((self.size[0]-self.length)/2+i,(self.size[1]-8)/2,'-')
				if self.numbers[self.length-1] >= 0:
					self.window.addstr((self.size[0]+self.length)/2-1,(self.size[1]-8)/2,'+'+(7-len(str(self.numbers[self.length-1])))*" "+str(self.numbers[self.length-1]),curses.A_UNDERLINE)
				else:	
					self.window.addstr((self.size[0]+self.length)/2-1,(self.size[1]-8)/2,'-'+(7-len(str(abs(self.numbers[self.length-1]))))*" "+str(abs(self.numbers[self.length-1])),curses.A_UNDERLINE)
				self.window.addstr((self.size[0]+self.length)/2,(self.size[1]-8)/2,'='+(7-len(str(self.sum)))*" "+str(self.sum),curses.A_UNDERLINE)

	
	def add(self):
		self.sum = 0
		for item in self.numbers:
			self.sum += item
	
	def clear(self):
		self.numbers = []
		self.sum = 0

	def set_numbers(self, list):
		self.numbers = list
		self.add()

curses.wrapper(MainMenu)

from sqlalchemy import Table, Column, Integer, String, MetaData, ForeignKey, create_engine, DateTime, Boolean, or_
from sqlalchemy.orm import sessionmaker, relationship, backref
from sqlalchemy.ext.declarative import declarative_base
import datetime
import conf

engine = create_engine(conf.db_url)
Base = declarative_base()
Session = sessionmaker(bind=engine)

class User(Base):
	__tablename__ = 'users'
	name = Column(String(10), primary_key=True)
	card = Column(String(10))
	rfid = Column(String(10))
	credit = Column(Integer)

	name_re = r"[a-z]+"
	card_re = r"(([Nn][Tt][Nn][Uu])?[0-9]+)?"
	rfid_re = r"[0-9]*"

	def __init__(self, name, card, rfid, credit=0):
		self.name = name
		if card == '':
			card = None
		self.card = card
		if rfid == '':
			rfid = None
		self.rfid = rfid
		self.credit = credit

	def __repr__(self):
		return "<User('%s')>" % self.name

	def __str__(self):
		return self.name

	def is_anonymous(self):
		return self.card == '11122233'

class Product(Base):
	__tablename__ = 'products'

	bar_code = Column(String(13), primary_key=True)
	name = Column(String(45))
	price = Column(Integer)
        stock = Column(Integer)

	bar_code_re = r"[0-9]+"
	name_re = r".+"
	name_length = 45

	def __init__(self, bar_code, name, price, stock=0):
		self.name = name
		self.bar_code = bar_code
		self.price = price
                self.stock = stock

	def __repr__(self):
		return "<Product('%s', '%s', '%s', '%s')>" % (self.name, self.bar_code, self.price, self.stock)

	def __str__(self):
		return self.name

class PurchaseEntry(Base):
	__tablename__ = 'purchase_entries'
	id = Column(Integer, primary_key=True)
	purchase_id = Column(Integer,ForeignKey("purchases.id"))
	product_bar_code = Column(String(13),ForeignKey("products.bar_code"))
	amount = Column(Integer)

	product = relationship(Product,backref="purchases")
        
	def __init__(self, purchase, product, amount):
		self.product = product
		self.product_bar_code = product.bar_code
		self.purchase = purchase
		self.amount = amount
	def __repr__(self):
		return "<PurchaseEntry('%s', '%s')>" % (self.product.name, self.amount )
		

class Transaction(Base):
	__tablename__ = 'transactions'

	id = Column(Integer, primary_key=True)
	time = Column(DateTime)
	user_name = Column(String(10), ForeignKey('users.name'))
	amount = Column(Integer)
	description = Column(String(50))
	purchase_id = Column(Integer, ForeignKey('purchases.id'))

	user = relationship(User, backref=backref('transactions', order_by=time))

	def __init__(self, user, amount=0, description=None, purchase=None):
		self.user = user
		self.amount = amount
		self.description = description
		self.purchase = purchase

	def perform_transaction(self):
		self.time = datetime.datetime.now()
		self.user.credit -= self.amount
		if self.purchase:
			for entry in self.purchase.entries:
				entry.product.stock -= entry.amount


class Purchase(Base):
	__tablename__ = 'purchases'
	
	id = Column(Integer, primary_key=True)
	time = Column(DateTime)
#	user_name = Column(Integer, ForeignKey('users.name'))
	price = Column(Integer)
#	performed = Column(Boolean)

#	user = relationship(User, backref=backref('purchases', order_by=id))
#	users = relationship(User, secondary=purchase_user, backref='purhcases'
	transactions = relationship(Transaction, order_by=Transaction.user_name, backref='purchase')
	entries = relationship(PurchaseEntry, backref=backref("purchase"))

	def __init__(self):
		pass

	def __repr__(self):
		return "<Purchase(%d, %d, '%s')>" % (self.id, self.price, self.time.strftime('%c'))

	def is_complete(self):
		return len(self.transactions) > 0 and len(self.entries) > 0

	def price_per_transaction(self):
		return self.price/len(self.transactions)

	def set_price(self):
		self.price = 0
		for entry in self.entries:
			self.price += entry.amount*entry.product.price
		if len(self.transactions) > 0:
			for t in self.transactions:
				t.amount = self.price_per_transaction()
	
	def perform_purchase(self):
		self.time = datetime.datetime.now()
		self.set_price()
		for t in self.transactions:
			t.perform_transaction()
#		self.user.credit -= self.price
#		self.performed = True

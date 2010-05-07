from sqlalchemy import Table, Column, Integer, String, MetaData, ForeignKey, create_engine, DateTime, Boolean, or_
from sqlalchemy.orm import sessionmaker, relationship, backref
from sqlalchemy.ext.declarative import declarative_base
import datetime

engine = create_engine('sqlite:///data')
Base = declarative_base()
Session = sessionmaker(bind=engine)

class User(Base):
	__tablename__ = 'users'
	name = Column(String(10), primary_key=True)
	card = Column(String(10))
	credit = Column(Integer)

	def __init__(self, name, card, credit=0):
		self.name = name
		self.card = card
		self.credit = credit

	def __repr__(self):
		return "<User('%s')>" % self.name

class Product(Base):
	__tablename__ = 'products'

	bar_code = Column(Integer, primary_key=True)
	name = Column(String(30))
	price = Column(Integer)

	def __init__(self, bar_code, name, price):
		self.name = name
		self.bar_code = bar_code
		self.price = price

	def __repr__(self):
		return "<Product('%s', '%s', '%s')>" % (self.name, self.bar_code, self.price)

class PurchaseEntry(Base):
	__tablename__ = 'purchase_entries'
	id = Column(Integer, primary_key=True)
	purchase_id = Column(Integer,ForeignKey("purchases.id"))
	product_bar_code = Column(Integer,ForeignKey("products.bar_code"))
	amount = Column(Integer)

	product = relationship(Product,backref="purchases")

	def __init__(self, purchase, product, amount):
		self.product = product
		self.product_bar_code = product.bar_code
		self.purchase_id = purchase.id
		self.amount = amount

	def __repr__(self):
		return "<PurchaseEntry('%s', '%s', '%s')>" % (self.purchase.user.user, self.product.name, self.amount )
		

class Purchase(Base):
	__tablename__ = 'purchases'
	
	id = Column(Integer, primary_key=True)
	time = Column(DateTime)
	user_name = Column(Integer, ForeignKey('users.name'))
	price = Column(Integer)
	performed = Column(Boolean)

	user = relationship(User, backref=backref('purchases', order_by=id))
	products = relationship(PurchaseEntry, backref=backref("purchase"))

	def __init__(self ,performed=False):
		self.performed = performed

	def __repr__(self):
		return "<Purchase('%s', '%s', '%s')>" % (self.user.name, self.price, self.time.strftime('%c'))

	def set_price(self):
		self.price = 0
		for entry in self.products:
			self.price += entry.amount*entry.product.price
	
	def perform_purchase(self):
		if self.performed:
			print "This transaction has already been performed"
		else:
			self.time = datetime.datetime.now()
			self.set_price()
			self.user.credit -= self.price
			self.performed = True

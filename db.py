from sqlalchemy import Column, Integer, String, ForeignKey, create_engine, DateTime, Boolean
from sqlalchemy.orm import sessionmaker, relationship, backref
from sqlalchemy.ext.declarative import declarative_base
from math import ceil, floor
import datetime
import conf

engine = create_engine(conf.db_url)
Base = declarative_base()
Session = sessionmaker(bind=engine)


class User(Base):
    __tablename__ = 'users'
    name = Column(String(10), primary_key=True)
    card = Column(String(20))
    rfid = Column(String(20))
    credit = Column(Integer)

    name_re = r"[a-z]+"
    card_re = r"(([Nn][Tt][Nn][Uu])?[0-9]+)?"
    rfid_re = r"[0-9a-fA-F]*"

    def __init__(self, name, card, rfid=None, credit=0):
        self.name = name
        if card == '':
            card = None
        self.card = card
        if rfid == '':
            rfid = None
        self.rfid = rfid
        self.credit = credit

    def __repr__(self):
        return f"<User('{self.name}')>"

    def __str__(self):
        return self.name

    def is_anonymous(self):
        return self.card == '11122233'


class Product(Base):
    __tablename__ = 'products'

    product_id = Column(Integer, primary_key=True)
    bar_code = Column(String(13))
    name = Column(String(45))
    price = Column(Integer)
    stock = Column(Integer)
    hidden = Column(Boolean, nullable=False, default=False)

    bar_code_re = r"[0-9]+"
    name_re = r".+"
    name_length = 45

    def __init__(self, bar_code, name, price, stock=0, hidden = False):
        self.name = name
        self.bar_code = bar_code
        self.price = price
        self.stock = stock
        self.hidden = hidden

    def __repr__(self):
        return f"<Product('{self.name}', '{self.bar_code}', '{self.price}', '{self.stock}', '{self.hidden}')>"

    def __str__(self):
        return self.name


class UserProducts(Base):
    __tablename__ = 'user_products'
    user_name = Column(String(10), ForeignKey('users.name'), primary_key=True)
    product_id = Column(Integer, ForeignKey("products.product_id"), primary_key=True)
    count = Column(Integer)
    sign = Column(Integer)

    user = relationship(User, backref=backref('products', order_by=count.desc()), lazy='joined')
    product = relationship(Product, backref="users", lazy='joined')


class PurchaseEntry(Base):
    __tablename__ = 'purchase_entries'
    id = Column(Integer, primary_key=True)
    purchase_id = Column(Integer, ForeignKey("purchases.id"))
    product_id = Column(Integer, ForeignKey("products.product_id"))
    amount = Column(Integer)

    product = relationship(Product, backref="purchases")

    def __init__(self, purchase, product, amount):
        self.product = product
        self.product_bar_code = product.bar_code
        self.purchase = purchase
        self.amount = amount

    def __repr__(self):
        return f"<PurchaseEntry('{self.product.name}', '{self.amount}')>"


class Transaction(Base):
    __tablename__ = 'transactions'

    id = Column(Integer, primary_key=True)
    time = Column(DateTime)
    user_name = Column(String(10), ForeignKey('users.name'))
    amount = Column(Integer)
    description = Column(String(50))
    purchase_id = Column(Integer, ForeignKey('purchases.id'))
    penalty = Column(Integer)

    user = relationship(User, backref=backref('transactions', order_by=time))

    def __init__(self, user, amount=0, description=None, purchase=None, penalty=1):
        self.user = user
        self.amount = amount
        self.description = description
        self.purchase = purchase
        self.penalty = penalty

    def perform_transaction(self, ignore_penalty=False):
        self.time = datetime.datetime.now()
        if not ignore_penalty:
            self.amount *= self.penalty
        self.user.credit -= self.amount


class Purchase(Base):
    __tablename__ = 'purchases'

    id = Column(Integer, primary_key=True)
    time = Column(DateTime)
    price = Column(Integer)

    transactions = relationship(Transaction, order_by=Transaction.user_name, backref='purchase')
    entries = relationship(PurchaseEntry, backref=backref("purchase"))

    def __init__(self):
        pass

    def __repr__(self):
        return f"<Purchase({int(self.id):d}, {self.price:d}, '{self.time.strftime('%c')}')>"

    def is_complete(self):
        return len(self.transactions) > 0 and len(self.entries) > 0

    def price_per_transaction(self, round_up=True):
        if round_up:
            return int(ceil(float(self.price)/len(self.transactions)))
        else:
            return int(floor(float(self.price)/len(self.transactions)))

    def set_price(self, round_up=True):
        self.price = 0
        for entry in self.entries:
            self.price += entry.amount*entry.product.price
        if len(self.transactions) > 0:
            for t in self.transactions:
                t.amount = self.price_per_transaction(round_up=round_up)

    def perform_purchase(self, ignore_penalty=False, round_up=True):
        self.time = datetime.datetime.now()
        self.set_price(round_up=round_up)
        for t in self.transactions:
            t.perform_transaction(ignore_penalty=ignore_penalty)
        for entry in self.entries:
            entry.product.stock -= entry.amount

    def perform_soft_purchase(self, price, round_up=True):
        self.time = datetime.datetime.now()
        self.price = price
        for t in self.transactions:
            t.amount = self.price_per_transaction(round_up=round_up)
        for t in self.transactions:
            t.perform_transaction()

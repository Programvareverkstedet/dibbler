#! /usr/bin/env python
# -*- coding: UTF-8 -*-

import datetime
from collections import defaultdict

from .helpers import *
from .models.db import *;

def getUser():
	while 1:
		string = input('user? ')
		session = Session()
		user = search_user(string, session)
		session.close()
		if not isinstance(user, list):	
			return user.name
		i=0
		if len(user)==0:
			print('no matching string')
		if len(user)==1:
			print('antar: ', user[0].name, '\n')
			return user[0].name
		if len(user)>10:
			continue
		for u in user:
			print(i, u.name)
			i += 1
		try:
			n = int(input ('enter number:'))
		except:
			print('invalid input, restarting')
			continue
		if (n>-1) and (n<i):
			return user[n].name
def getProduct():	
	while 1:
		string = input('product? ')
		session = Session()
		product = search_product(string, session)
		session.close()
		if not isinstance(product, list):	
			return product.name
		i=0
		if len(product)==0:
			print('no matching string')
		if len(product)==1:
			print('antar: ', product[0].name, '\n')
			return product[0].name
		if len(product)>10:
			continue
		for u in product:
			print(i, u.name)
			i += 1
		try:
			n = int(input ('enter number:'))
		except:
			print('invalid input, restarting')
			continue
		if (n>-1) and (n<i):
			return product[n].name

class Database:
	#for varer
	varePersonAntall = defaultdict(dict) #varePersonAntall[Oreo][trygvrad] == 3
	vareDatoAntall = defaultdict(list) #dict->array
	vareUkedagAntall = defaultdict(list)
	#for personer
	personVareAntall = defaultdict(dict) #personVareAntall[trygvrad][Oreo] == 3
	personVareVerdi = defaultdict(dict) #personVareVerdi[trygvrad][Oreo] == 30 #[kr]
	personDatoVerdi = defaultdict(list) #dict->array
	personUkedagVerdi = defaultdict(list)
	#for global
	personPosTransactions = {} # personPosTransactions[trygvrad] == 100 #trygvrad har lagt 100kr i boksen
	personNegTransactions = {} # personNegTransactions[trygvrad» == 70 #trygvrad har tatt 70kr fra boksen
	globalVareAntall = {}#globalVareAntall[Oreo] == 3
	globalVareVerdi = {}#globalVareVerdi[Oreo] == 30 #[kr]
	globalPersonAntall = {}#globalPersonAntall[trygvrad] == 3
	globalPersonForbruk = {}#globalPersonVerdi == 30 #[kr]
	globalUkedagForbruk = []
	globalDatoVarer = [] 
	globalDatoForbruk = []
	pengebeholdning = []

class InputLine:
	def __init__(self, u, p, t):
		self.inputUser = u
		self.inputProduct = p
		self.inputType = t

def getDateDb(date, inp):
	try:
		year = inp.partition('-')
		month = year[2].partition('-')
		return datetime.datetime(int(year[0]), int(month[0]), int(month[2]))
	except:
		print('invalid date, setting date to date found in db')
		print(date)
		return date

def dateToDateNumDb(date, startDate):
	deltaDays = date-startDate
	return int(deltaDays.days), date.weekday()

def getInputType():
	inp = 0
	while not (inp == '1' or inp == '2' or inp == '3' or inp == '4'):
		print('type 1 for user-statistics')
		print('type 2 for product-statistics')
		print('type 3 for global-statistics')
		print('type 4 to enter loop-mode')
		inp = input('')
	return int(inp)

def getProducts(products):
	product = []
	products = products.partition('¤')
	product.append(products[0])
	while (products[1]=='¤'):
		products = products[2].partition('¤')
		product.append(products[0])
	return product

def getDateFile(date, inp):
	try:
		year = inp.partition('-')
		month = year[2].partition('-')
		return datetime.date(int(year[0]), int(month[0]), int(month[2]))	
	except:
		print('invalid date, setting date to date found on file file')
		print(date)
		return datetime.date(int(date.partition('-')[0]), int(date.partition('-')[2].partition('-')[0]), int(date.partition('-')[2].partition('-')[2]))

def dateToDateNumFile(date, startDate):
	year = date.partition('-')
	month = year[2].partition('-')
	day =  datetime.date(int(year[0]), int(month[0]), int(month[2]))
	deltaDays = day-startDate
	return int(deltaDays.days), day.weekday()
	
def clearDatabase(database):
	database.varePersonAntall.clear()
	database.vareDatoAntall.clear()
	database.vareUkedagAntall.clear()
	database.personVareAntall.clear()
	database.personVareVerdi.clear()
	database.personDatoVerdi.clear()
	database.personUkedagVerdi.clear()
	database.personPosTransactions.clear()
	database.personNegTransactions.clear()
	database.globalVareAntall.clear()
	database.globalVareVerdi.clear()
	database.globalPersonAntall.clear()
	database.globalPersonForbruk.clear()
	return(database)

def addLineToDatabase(database, inputLine):
	if abs(inputLine.price)>90000:
		return database
	#fyller inn for varer
	if (not inputLine.product=='') and ((inputLine.inputProduct=='') or (inputLine.inputProduct==inputLine.product)):
		database.varePersonAntall[inputLine.product][inputLine.user] = database.varePersonAntall[inputLine.product].setdefault(inputLine.user,0) + 1	
		if inputLine.product not in database.vareDatoAntall:
			database.vareDatoAntall[inputLine.product] = [0]*(inputLine.numberOfDays+1)
		database.vareDatoAntall[inputLine.product][inputLine.dateNum] += 1
		if inputLine.product not in database.vareUkedagAntall:
			database.vareUkedagAntall[inputLine.product] = [0]*7
		database.vareUkedagAntall[inputLine.product][inputLine.weekday] += 1
	#fyller inn for personer
	if (inputLine.inputUser=='') or (inputLine.inputUser==inputLine.user):
		if not inputLine.product == '':
			database.personVareAntall[inputLine.user][inputLine.product] = database.personVareAntall[inputLine.user].setdefault(inputLine.product,0) + 1
			database.personVareVerdi[inputLine.user][inputLine.product] = database.personVareVerdi[inputLine.user].setdefault(inputLine.product,0) + inputLine.price
			if inputLine.user not in database.personDatoVerdi:
				database.personDatoVerdi[inputLine.user] = [0]*(inputLine.numberOfDays+1)
			database.personDatoVerdi[inputLine.user][inputLine.dateNum] += inputLine.price
			if inputLine.user not in database.personUkedagVerdi:
				database.personUkedagVerdi[inputLine.user] = [0]*7
			database.personUkedagVerdi[inputLine.user][inputLine.weekday] += inputLine.price
	#fyller inn delt statistikk (genereres uansett)
	if (inputLine.product==''):
		if (inputLine.price>0):
			database.personPosTransactions[inputLine.user] = database.personPosTransactions.setdefault(inputLine.user,0) + inputLine.price
		else:
			database.personNegTransactions[inputLine.user] = database.personNegTransactions.setdefault(inputLine.user,0) + inputLine.price
	elif not (inputLine.inputType==1):
		database.globalVareAntall[inputLine.product] = database.globalVareAntall.setdefault(inputLine.product,0) + 1
		database.globalVareVerdi[inputLine.product] = database.globalVareVerdi.setdefault(inputLine.product,0) + inputLine.price
					
	#fyller inn for global statistikk
	if (inputLine.inputType==3) or (inputLine.inputType==4):
		database.pengebeholdning[inputLine.dateNum] += inputLine.price
		if not (inputLine.product==''):
			database.globalPersonAntall[inputLine.user] = database.globalPersonAntall.setdefault(inputLine.user,0) + 1
			database.globalPersonForbruk[inputLine.user] = database.globalPersonForbruk.setdefault(inputLine.user,0) + inputLine.price
			database.globalDatoVarer[inputLine.dateNum] += 1
			database.globalDatoForbruk[inputLine.dateNum] += inputLine.price
			database.globalUkedagForbruk[inputLine.weekday] += inputLine.price
	return database

def buildDatabaseFromDb(inputType, inputProduct, inputUser):
	sdate = input('enter start date (yyyy-mm-dd)? ')
	edate = input('enter end date (yyyy-mm-dd)? ')
	print('building database...')	
	session = Session()
	transaction_list = session.query(Transaction).all()
	inputLine = InputLine(inputUser, inputProduct, inputType)
	startDate = getDateDb(transaction_list[0].time, sdate)
	endDate = getDateDb(transaction_list[-1].time, edate)
	inputLine.numberOfDays = (endDate-startDate).days
	database = Database()
	database = clearDatabase(database)

	if (inputType==3) or (inputType==4):
		database.globalDatoVarer = [0]*(inputLine.numberOfDays+1)
		database.globalDatoForbruk = [0]*(inputLine.numberOfDays+1)
		database.globalUkedagForbruk = [0]*7
		database.pengebeholdning = [0]*(inputLine.numberOfDays+1)
	print('wait for it.... ')
	for transaction in transaction_list:
		if transaction.purchase:
			products = [ent.product.name for ent in transaction.purchase.entries]
		else:
			products = []
			products.append('')
		inputLine.dateNum, inputLine.weekday = dateToDateNumDb(transaction.time, startDate)
		if inputLine.dateNum<0 or inputLine.dateNum>(inputLine.numberOfDays):
			continue
		inputLine.user=transaction.user.name
		inputLine.price=transaction.amount
		for inputLine.product in products:	
			database=addLineToDatabase(database, inputLine )
			inputLine.price = 0;

	print('saving as default.dibblerlog...', end=' ')
	f=open('default.dibblerlog','w')	
	line_format = '%s|%s|%s|%s|%s|%s\n'
	transaction_list = session.query(Transaction).all()
	for transaction in transaction_list:
		if transaction.purchase:
			products = '¤'.join([ent.product.name for ent in transaction.purchase.entries])
			description = ''
		else:
			products = ''
			description = transaction.description
		line = line_format % ('purchase', transaction.time, products, transaction.user.name, transaction.amount, transaction.description)
		f.write(line.encode('utf8'))
	session.close()
	f.close
	#bygg database.pengebeholdning
	if (inputType==3) or (inputType==4):
		for i in range(inputLine.numberOfDays+1):
			if i > 0:
				database.pengebeholdning[i] +=database.pengebeholdning[i-1]
	#bygg dateLine
	day=datetime.timedelta(days=1)
	dateLine=[]
	dateLine.append(startDate)
	for n in range(inputLine.numberOfDays):
		dateLine.append(startDate+n*day)
	print('done')
	return database, dateLine

def buildDatabaseFromFile(inputFile, inputType, inputProduct, inputUser):
	sdate = input('enter start date (yyyy-mm-dd)? ')
	edate = input('enter end date (yyyy-mm-dd)? ')
		
	f=open(inputFile)
	try:
		fileLines=f.readlines()
	finally:
		f.close()
	inputLine = InputLine(inputUser, inputProduct, inputType)
	startDate = getDateFile(fileLines[0].partition('|')[2].partition(' ')[0], sdate)
	endDate = getDateFile(fileLines[-1].partition('|')[2].partition(' ')[0], edate)
	inputLine.numberOfDays = (endDate-startDate).days
	database = Database()
	database = clearDatabase(database)

	if (inputType==3) or (inputType==4):
		database.globalDatoVarer = [0]*(inputLine.numberOfDays+1)
		database.globalDatoForbruk = [0]*(inputLine.numberOfDays+1)
		database.globalUkedagForbruk = [0]*7
		database.pengebeholdning = [0]*(inputLine.numberOfDays+1)
	for linje in fileLines:
		if not (linje[0]=='#') and not (linje=='\n') :
			#henter dateNum, products, user, price
			restDel = linje.partition('|')
			restDel = restDel[2].partition(' ')
			inputLine.dateNum, inputLine.weekday = dateToDateNumFile(restDel[0], startDate)
			if inputLine.dateNum<0 or inputLine.dateNum>(inputLine.numberOfDays):
				continue
			restDel=restDel[2].partition('|')
			restDel=restDel[2].partition('|')
			products = restDel[0]
			restDel=restDel[2].partition('|')
			inputLine.user=restDel[0]
			inputLine.price=int(restDel[2].partition('|')[0])
			for inputLine.product in getProducts(products):	
				database=addLineToDatabase(database, inputLine )
				inputLine.price = 0;
	#bygg database.pengebeholdning
	if (inputType==3) or (inputType==4):
		for i in range(inputLine.numberOfDays+1):
			if i > 0:
				database.pengebeholdning[i] +=database.pengebeholdning[i-1]
	#bygg dateLine
	day=datetime.timedelta(days=1)
	dateLine=[]
	dateLine.append(startDate)
	for n in range(inputLine.numberOfDays):
		dateLine.append(startDate+n*day)
	return database, dateLine

def printTopDict(dictionary, n, k):
	i=0
	for key in sorted(dictionary, key=dictionary.get, reverse=k):
		print(key, ': ',dictionary[key]) 
		if i<n:
			i += 1
		else:
			break

def printTopDict2(dictionary, dictionary2, n):
	print('')
	print('product :  price[kr] ( number )')
	i=0
	for key in sorted(dictionary, key=dictionary.get, reverse=True):
		print(key, ': ',dictionary[key], ' (', dictionary2[key], ') ') 
		if i<n:
			i += 1
		else:
			break

def printWeekdays(week, days):
	if week==[] or days==0:
		return
	print('mon: ', '%.2f'%(week[0]*7.0/days), ' tue: ', '%.2f'%(week[1]*7.0/days), ' wen: ', '%.2f'%(week[2]*7.0/days), ' thu: ', '%.2f'%(week[3]*7.0/days), ' fri: ', '%.2f'%(week[4]*7.0/days), ' sat: ','%.2f'%( week[5]*7.0/days), ' sun: ', '%.2f'%(week[6]*7.0/days))
	print('forbruk per dag (snitt): ', '%.2f'%(sum(week)*1.0/days))
	print('')

def printBalance(database, user):
	forbruk = 0
	if (user in database.personVareVerdi):
		forbruk = sum([i for i in list(database.personVareVerdi[user].values())])
		print('totalt kjøpt for: ', forbruk, end=' ') 
	if  (user in database.personNegTransactions):
		print('kr, totalt lagt til: ', -database.personNegTransactions[user], end=' ') 
		forbruk=-database.personNegTransactions[user]-forbruk
	if  (user in database.personPosTransactions):
		print('kr, totalt tatt fra boks: ', database.personPosTransactions[user], end=' ') 
		forbruk=forbruk-database.personPosTransactions[user]
	print('balanse: ', forbruk, 'kr', end=' ')
	print('')

def printUser(database, dateLine, user, n):
	printTopDict2(database.personVareVerdi[user], database.personVareAntall[user], n)
	print('\nforbruk per ukedag [kr/dag],', end=' ')
	printWeekdays(database.personUkedagVerdi[user], len(dateLine))
	printBalance(database, user)

def printProduct(database, dateLine, product, n):
	printTopDict(database.varePersonAntall[product], n, 1)
	print('\nforbruk per ukedag [antall/dag],', end=' ')
	printWeekdays(database.vareUkedagAntall[product], len(dateLine))
	print('Det er solgt: ', database.globalVareAntall[product], product, 'til en verdi av: ', database.globalVareVerdi[product], 'kr') 

def printGlobal(database, dateLine, n):
	print('\nmest lagt til: ')
	printTopDict(database.personNegTransactions, n, 0)
	print('\nmest tatt fra:')
	printTopDict(database.personPosTransactions, n, 1)
	print('\nstørst forbruk:')
	printTopDict(database.globalPersonForbruk, n, 1)
	printTopDict2(database.globalVareVerdi, database.globalVareAntall, n)
	print('\nforbruk per ukedag [kr/dag],', end=' ')
	printWeekdays(database.globalUkedagForbruk, len(dateLine))
	print('Det er solgt varer til en verdi av: ', sum(database.globalDatoForbruk), 'kr, det er lagt til', -sum([i for i in list(database.personNegTransactions.values())]), 'og tatt fra', sum([i for i in list(database.personPosTransactions.values())]), end=' ')
	print('balansen blir:', database.pengebeholdning[len(dateLine)-1], 'der negative verdier representerer at brukere har kreditt tilgjengelig')

def alt4menuTextOnly(database, dateLine):
	n=10
	while 1:		
		print('\n1: user-statistics, 2: product-statistics, 3:global-statistics, n: adjust amount of data shown q:quit')
		inp = input('')
		if inp == 'q':
			break
		elif inp == '1':
			try:
				printUser(database, dateLine, getUser(), n)
			except:
				print('\n\nSomething is not right, (last date prior to first date?)')
		elif inp == '2':
			try:
				printProduct(database, dateLine, getProduct(), n)
			except:
				print('\n\nSomething is not right, (last date prior to first date?)')
		elif inp == '3':
			try:
				printGlobal(database, dateLine, n)
			except:
				print('\n\nSomething is not right, (last date prior to first date?)')
		elif inp == 'n':
			n=int(input('set number to show '));

def statisticsTextOnly():
	inputType = 4
	product = ''
	user = '' 
	print('\n0: from file, 1: from database, q:quit')
	inp = input('')
	if inp == '1':
		database, dateLine = buildDatabaseFromDb(inputType, product, user)
	elif inp=='0' or inp == '':
		database, dateLine = buildDatabaseFromFile('default.dibblerlog', inputType, product, user)
	if not inp == 'q':
		alt4menuTextOnly(database, dateLine)

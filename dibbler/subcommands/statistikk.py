#! /usr/bin/env python

# TODO: fixme

# -*- coding: UTF-8 -*-
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from dibbler.lib.statistikkHelpers import *


def getInputType():
    inp = 0
    while not (inp == "1" or inp == "2" or inp == "3" or inp == "4"):
        print("type 1 for user-statistics")
        print("type 2 for product-statistics")
        print("type 3 for global-statistics")
        print("type 4 to enter loop-mode")
        inp = input("")
    return int(inp)


def getDateFile(date, n):
    try:
        if n == 0:
            inp = input("start date? (yyyy-mm-dd) ")
        elif n == -1:
            inp = input("end date? (yyyy-mm-dd) ")
        year = inp.partition("-")
        month = year[2].partition("-")
        return datetime.date(int(year[0]), int(month[0]), int(month[2]))
    except:
        print("invalid date, setting start start date")
        if n == 0:
            print("to date found on first line")
        elif n == -1:
            print("to date found on last line")
        print(date)
        return datetime.date(
            int(date.partition("-")[0]),
            int(date.partition("-")[2].partition("-")[0]),
            int(date.partition("-")[2].partition("-")[2]),
        )


def dateToDateNumFile(date, startDate):
    year = date.partition("-")
    month = year[2].partition("-")
    day = datetime.date(int(year[0]), int(month[0]), int(month[2]))
    deltaDays = day - startDate
    return int(deltaDays.days), day.weekday()


def getProducts(products):
    product = []
    products = products.partition("¤")
    product.append(products[0])
    while products[1] == "¤":
        products = products[2].partition("¤")
        product.append(products[0])
    return product


def piePlot(dictionary, n):
    keys = []
    values = []
    i = 0
    for key in sorted(dictionary, key=dictionary.get, reverse=True):
        values.append(dictionary[key])
        if i < n:
            keys.append(key)
            i += 1
        else:
            keys.append("")
    plt.pie(values, labels=keys)


def datePlot(array, dateLine):
    if not array == []:
        plt.bar(dateLine, array)
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter("%b"))


def dayPlot(array, days):
    if not array == []:
        for i in range(7):
            array[i] = array[i] * 7.0 / days
        plt.bar(list(range(7)), array)
        plt.xticks(
            list(range(7)),
            [
                "      mon",
                "      tue",
                "      wed",
                "      thu",
                "      fri",
                "      sat",
                "      sun",
            ],
        )


def graphPlot(array, dateLine):
    if not array == []:
        plt.plot(dateLine, array)
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter("%b"))


def plotUser(database, dateLine, user, n):
    printUser(database, dateLine, user, n)
    plt.subplot(221)
    piePlot(database.personVareAntall[user], n)
    plt.xlabel("antall varer kjøpt gjengitt i antall")
    plt.subplot(222)
    datePlot(database.personDatoVerdi[user], dateLine)
    plt.xlabel("penger brukt over dato")
    plt.subplot(223)
    piePlot(database.personVareVerdi[user], n)
    plt.xlabel("antall varer kjøpt gjengitt i verdi")
    plt.subplot(224)
    dayPlot(database.personUkedagVerdi[user], len(dateLine))
    plt.xlabel("forbruk over ukedager")
    plt.show()


def plotProduct(database, dateLine, product, n):
    printProduct(database, dateLine, product, n)
    plt.subplot(221)
    piePlot(database.varePersonAntall[product], n)
    plt.xlabel("personer som har handler produktet")
    plt.subplot(222)
    datePlot(database.vareDatoAntall[product], dateLine)
    plt.xlabel("antall produkter handlet per dag")
    # plt.subplot(223)
    plt.subplot(224)
    dayPlot(database.vareUkedagAntall[product], len(dateLine))
    plt.xlabel("antall over ukedager")
    plt.show()


def plotGlobal(database, dateLine, n):
    printGlobal(database, dateLine, n)
    plt.subplot(231)
    piePlot(database.globalVareVerdi, n)
    plt.xlabel("varer kjøpt gjengitt som verdi")
    plt.subplot(232)
    datePlot(database.globalDatoForbruk, dateLine)
    plt.xlabel("forbruk over dato")
    plt.subplot(233)
    graphPlot(database.pengebeholdning, dateLine)
    plt.xlabel("pengebeholdning over tid (negativ verdi utgjør samlet kreditt)")
    plt.subplot(234)
    piePlot(database.globalPersonForbruk, n)
    plt.xlabel("penger brukt av personer")
    plt.subplot(235)
    dayPlot(database.globalUkedagForbruk, len(dateLine))
    plt.xlabel("forbruk over ukedager")
    plt.show()


def alt4menu(database, dateLine, useDatabase):
    n = 10
    while 1:
        print(
            "\n1: user-statistics, 2: product-statistics, 3:global-statistics, n: adjust amount of data shown q:quit"
        )
        try:
            inp = input("")
        except:
            continue
        if inp == "q":
            break
        elif inp == "1":
            if i == "0":
                user = input("input full username: ")
            else:
                user = getUser()
            plotUser(database, dateLine, user, n)
        elif inp == "2":
            if i == "0":
                product = input("input full product name: ")
            else:
                product = getProduct()
            plotProduct(database, dateLine, product, n)
        elif inp == "3":
            plotGlobal(database, dateLine, n)
        elif inp == "n":
            try:
                n = int(input("set number to show "))
            except:
                pass


def main():
    inputType = getInputType()
    i = input("0:fil, 1:database \n? ")
    if inputType == 1:
        if i == "0":
            user = input("input full username: ")
        else:
            user = getUser()
        product = ""
    elif inputType == 2:
        if i == "0":
            product = input("input full product name: ")
        else:
            product = getProduct()
        user = ""
    else:
        product = ""
        user = ""
    if i == "0":
        inputFile = input("logfil? ")
        if inputFile == "":
            inputFile = "default.dibblerlog"
        database, dateLine = buildDatabaseFromFile(inputFile, inputType, product, user)
    else:
        database, dateLine = buildDatabaseFromDb(inputType, product, user)

    if inputType == 1:
        plotUser(database, dateLine, user, 10)
    if inputType == 2:
        plotProduct(database, dateLine, product, 10)
    if inputType == 3:
        plotGlobal(database, dateLine, 10)
    if inputType == 4:
        alt4menu(database, dateLine, i)


if __name__ == "__main__":
    main()

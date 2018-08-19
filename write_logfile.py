#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
import db
from helpers import *

# Writes a log of all transactions to a text file.
#
# Usage:
# ./write_logfile.py filename
# or (writing to stdout):
# ./write_logfile.py

def write_log(f):
    session = Session()
    line_format = '%s|%s|%s|%s|%s|%s\n'
    transaction_list = session.query(Transaction).all()
    for transaction in transaction_list:
        if transaction.purchase:
            products = ', '.join([ent.product.name for ent in transaction.purchase.entries])
            description = ''
        else:
            products = ''
            description = transaction.description
        line = line_format % ('purchase', transaction.time, products,
                              transaction.user.name, transaction.amount, transaction.description)
        f.write(line.encode('utf8'))
    session.close()

if len(sys.argv) < 2:
    write_log(sys.stdout)
else:
    filename = sys.argv[1]
    print('Writing log to ' + filename)
    with open(filename, 'w') as f:
        write_log(f)

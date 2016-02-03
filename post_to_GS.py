#!/usr/bin/python
# -*- coding: utf-8 -*-

import json
import gspread
from oauth2client.client import SignedJwtAssertionCredentials

json_key = json.load(open('gs_client_secret.json'))
scope = ['https://spreadsheets.google.com/feeds']

credentials = SignedJwtAssertionCredentials(json_key['client_email'], json_key['private_key'].encode(), scope)

gc = gspread.authorize(credentials)
# Check if the input URL can actually be used.
try:
    wks = gc.open_by_url('https://docs.google.com/spreadsheets/d/1BvbCYspFThW22z62v20Z-a-P4YZprMRJZwJd8qgQYkA/edit').worksheet('Monthly Budget')
except (ValueError, NameError):
    print "Invalid URL"

def find_next_avaliable_cell(col):
    values = wks.col_values(col)
    print values
    for value in values:
        if value == '':
            index = values.index(value)
            break
    return index + 1

with open('uber_receipts.json','r') as input_json:
    data = json.load(input_json)
    for item in data:
        row = find_next_avaliable_cell(9)
        wks.update_cell(row,9,item['date'])
        wks.update_cell(row,10,item['total'])

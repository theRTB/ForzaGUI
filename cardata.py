# -*- coding: utf-8 -*-
"""
Created on Tue May  2 20:00:13 2023

@author: RTB
"""

#TODO: make a proper tsv out of fh5_cars_kudosprime2.tsv

import csv
from os.path import exists

#maxlen model 46, maxlen maker 24, maxlen group 21 : 2023-04-32
NAMESTRING = lambda data: "{maker} {model} ({year}) {group} PI:{car_performance_index} o{car_ordinal}".format(**data)

class CarData():
    FILENAME = 'fh5_cars_kudosprime2.tsv'
    AS_INTEGER = ['car_ordinal', 'year', 'weight']
    INDEX = 'car_ordinal'
    
    data = {}
    if exists(FILENAME):
        with open(FILENAME, encoding='ISO-8859-1') as rawcsv:
            csvobject = csv.DictReader(rawcsv, delimiter='\t')
            for row in csvobject:
                if row[INDEX] == '':
                    print(f'missing ordinal: {row}')
                    continue
                for k, v in row.items():
                    row[k] = int(v) if (k in AS_INTEGER and v != '') else v
                data[row[INDEX]] = row
    else:
        print(f'file {FILENAME} does not exist, no cardata available')
                
    @classmethod
    def getinfo(cls, num):
        return cls.data.get(num, None)
# -*- coding: utf-8 -*-
"""
Created on Tue May  2 20:00:13 2023

@author: RTB
"""

import csv
from os.path import exists

class CarData():
    firstrow = []
    data = []
    filename = 'fh5_cars_kudosprime2.tsv'
    
    if exists(filename):
        with open(filename, encoding='ISO-8859-1') as rawcsv:
            csvobject = csv.reader(rawcsv, delimiter='\t')
            firstrow = next(csvobject)
            for row in csvobject: #convert column 5 to integer from string
                row[4] = int(row[4]) if row[4] != '' else row[4]
                data.append(row)  
                
    @classmethod
    def getinfo(cls, num):
        for row in CarData.data:
            if row[4] == num:
                return dict(zip(CarData.firstrow, row))
        return None
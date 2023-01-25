# -*- coding: utf-8 -*-
"""
Created on Sat Jun  4 11:59:00 2022

@author: RTB
"""

import tkinter
import tkinter.ttk

import csv

from os.path import exists

#import statistics

import constants
#import math

class GUICarInfoDummy:
    def __init__(self, logger):
        pass

    def display(self):
        pass

    def update(self, fdp):
        pass
    
    def set_canvas(self, frame):
        pass
    
    def reset(self):
        pass
    
    # def writeback(self):
    #     pass

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
    
class GUICarInfo:
    def __init__(self, logger):
        self.logger = logger
                
        self.maker_var = tkinter.StringVar()
        self.model_var = tkinter.StringVar()
        self.year_var = tkinter.StringVar()
        self.group_var = tkinter.StringVar()
        
        self.reset()
                    
    def display(self):    
        self.maker_var.set(f'{self.maker}')
        self.model_var.set(f'{self.model}')
        self.year_var.set(f'{self.year}')
        self.group_var.set(f'{self.group}')

    def update(self, fdp):
        if fdp.car_ordinal == 0:
            return
        
        if self.car_ordinal != fdp.car_ordinal:
            self.car_ordinal = fdp.car_ordinal
            row = CarData.getinfo(self.car_ordinal)
            
            if row is None:
                self.reset()
                return
            
            for key, value in row.items():
                setattr(self, key, value)
    
    def set_canvas(self, frame):
        self.frame = tkinter.Frame(frame, border=0, bg=constants.background_color, relief="groove",
                                            highlightthickness=True, highlightcolor=constants.text_color)
        
        opts = {'bg':constants.background_color, 'fg':constants.text_color, 'font':('Helvetica 15 bold')}
        tkinter.Label(self.frame, text="Maker", **opts).grid(row=0)
        tkinter.Label(self.frame, text="Model:", **opts).grid(row=1)
        tkinter.Label(self.frame, text="Year:", **opts).grid(row=2)
        tkinter.Label(self.frame, text="Group:", **opts).grid(row=3)
        
        opts = {'bg':constants.background_color, 'justify':tkinter.LEFT, 'width':40,
                'fg':constants.text_color, 'font':('Helvetica 15 bold')}
        tkinter.Entry(self.frame, textvariable=self.maker_var, **opts).grid(row=0, column=1)
        tkinter.Entry(self.frame, textvariable=self.model_var, **opts).grid(row=1, column=1)
        tkinter.Entry(self.frame, textvariable=self.year_var, **opts).grid(row=2, column=1)
        tkinter.Entry(self.frame, textvariable=self.group_var, **opts).grid(row=3, column=1)
    
    def reset(self):
        self.car_ordinal = None
        self.maker = "Please"      
        self.model = "Update"
        self.year = "the"
        self.group = "TSV"
                
        self.display()
        

'''
TODO: update fdp.py with:
First 4bytes of hznUnk is int

    case 11: return “Modern Super Cars”;
    case 12: return “Retro Super Cars”;
    case 13: return “Hyper Cars”;
    case 14: return “Retro Saloons”;
    case 16: return “Vans & Utility”;
    case 17: return “Retro Sports Cars”;
    case 18: return “Modern Sports Cars”;
    case 19: return “Super Saloons”;
    case 20: return “Classic Racers”;
    case 21: return “Cult Cars”;
    case 22: return “Rare Classics”;
    case 25: return “Super Hot Hatch”;
    case 29: return “Rods & Customs”;
    case 30: return “Retro Muscle”;
    case 31: return “Modern Muscle”;
    case 32: return “Retro Rally”;
    case 33: return “Classic Rally”;
    case 34: return “Rally Monsters”;
    case 35: return “Modern Rally”;
    case 36: return “GT Cars”;
    case 37: return “Super GT”;
    case 38: return “Extreme Offroad”;
    case 39: return “Sports Utility Heroes”;
    case 40: return “Offroad”;
    case 41: return “Offroad Buggies”;
    case 42: return “Classic Sports Cars”;
    case 43: return “Track Toys”;
    case 44: return “Vintage Racers”;
    case 45: return “Trucks”;
'''
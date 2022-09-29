# -*- coding: utf-8 -*-
"""
Created on Sun Feb 13 15:16:10 2022

@author: RTB
"""

import tkinter
import tkinter.ttk

from collections import deque
import statistics

import constants
import math

class GUISuspensionDummy:
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

TIRES = ['FL', 'FR', 'RL', 'RR']

class Suspension ():
    def __init__ (self, maxlen=60):
        self.maxlen=maxlen
        
        self.min = 999
        self.max = 0
        self.avg = deque(maxlen=self.maxlen)
        self.cur = 0
        
        self.min_var = tkinter.StringVar()
        self.max_var = tkinter.StringVar()
        self.cur_var = tkinter.StringVar()
        self.avg_var = tkinter.StringVar()
        self.reset()
        
    def reset(self):
        self.min = 999
        self.max = 0
        self.avg.extend([0]*self.maxlen)
        self.cur = 0
        
        self.min_var.set(" 0.00")
        self.max_var.set(" 0.00")
        self.cur_var.set(" 0.00")
        self.avg_var.set(" 0.00")
    

class GUISuspension:
    def __init__(self, logger):
        self.logger = logger
                
        self.suspension = {x:Suspension() for x in TIRES}
            

    def display(self):
        for x in TIRES:
            tire = self.suspension[x]
            tire.min_var.set(f"{tire.min*100: >2.2f}") 
            tire.max_var.set(f"{tire.max*100: >2.2f}") 
            tire.avg_var.set(f"{statistics.mean(tire.avg)*100: >2.2f}") 
            tire.cur_var.set(f"{tire.cur*100: >2.2f}") 

    def update(self, fdp):
        for x in TIRES:
            tire = self.suspension[x]
            val = getattr(fdp, f"suspension_travel_meters_{x}")
            tire.min = min(tire.min, val)
            tire.max = max(tire.max, val)
            tire.cur = val
            tire.avg.append(val)
    
    def set_canvas(self, frame):
        self.frame = tkinter.Frame(frame, border=0, bg=constants.background_color, relief="groove",
                                   highlightthickness=True, highlightcolor=constants.text_color)
        
        opts = {'bg':constants.background_color, 'fg':constants.text_color, 'font':('Helvetica 12 bold')}
        tkinter.Label(self.frame, text="Suspension (cm)", **opts).grid(row=1, columnspan=6)
              
        tkinter.Label(self.frame, text="minimum", **opts).grid(row=2, column=1, columnspan=2) 
        tkinter.Label(self.frame, text="avg (1s)", **opts).grid(row=2, column=4, columnspan=2) 
        tkinter.Label(self.frame, text="maximum", **opts).grid(row=5, column=1, columnspan=2) 
        tkinter.Label(self.frame, text="current", **opts).grid(row=5, column=4, columnspan=2) 
        
        opts['justify'] = tkinter.RIGHT
        opts['anchor'] = tkinter.E
        opts['font'] = ('Helvetica 14 bold italic')
        opts['width'] = 6 
        # min avg
        # max cur
        for i, x in enumerate(TIRES):
            row = int(i/2)+3
            column = i%2 + 1
            tkinter.Label(self.frame, textvariable=self.suspension[x].min_var, **opts).grid(row=row, column=column)     
            tkinter.Label(self.frame, textvariable=self.suspension[x].max_var, **opts).grid(row=row+3, column=column) 
            tkinter.Label(self.frame, textvariable=self.suspension[x].avg_var, **opts).grid(row=row, column=column+3)  
            tkinter.Label(self.frame, textvariable=self.suspension[x].cur_var, **opts).grid(row=row+3, column=column+3)   
    
    def reset(self):
        for x in TIRES:
            self.suspension[x].reset()
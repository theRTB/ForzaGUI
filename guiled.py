# -*- coding: utf-8 -*-
"""
Created on Sun Feb 13 15:16:10 2022

@author: RTB
"""

import tkinter
import tkinter.ttk

import constants
import math


import matplotlib.pyplot as plt
import numpy as np

from dragderivation import Trace, DragDerivation

tanh_offset = lambda x: 1 - math.tanh(0.31 * min(x, 5) + 0.76)


#TODO:
    #include reaction time offset to optimal shift
    #add interpolation and smoothing to collected rpm values per frame
    #add hysteresis to the rpm value before updating state
    

BLACK = '#000000'
GREEN = '#80FF80'
AMBER = '#FFBF7F'
RED   = '#FF8088'
BLUE  = '#8080FF'

ILLUMINATION_INTERVAL = int(1.6*60) #1.6 seconds
REACTION_TIME = 5 #83 milliseconds
DISTANCE_FROM_REVLIMIT = 5 #83 milliseconds

STATES = [
    [BLACK]*10,
    [GREEN, GREEN] + [BLACK]*8,
    [GREEN, GREEN, AMBER, AMBER] + [BLACK]*6,
    [GREEN, GREEN, AMBER, AMBER, AMBER, AMBER, ] + [BLACK]*4,
    [GREEN, GREEN, AMBER, AMBER, AMBER, AMBER, RED, RED] + [BLACK]*2,
    [BLUE]*10,
    [RED, BLUE, RED, BLUE, RED, RED, BLUE, RED, BLUE, RED] ]

class GUILedDummy:
    def __init__(self, logger):
        pass
        
    def set_rpmtable(self, rpmtable, rpmvalues, gears, revlimit, collectedingear, trace):
        pass
        
    def update (self, fdp):
        pass

    def update_leds(self):
        pass
    
    def set_canvas(self, frame):
        pass
    
    def reset(self):
        pass

class GUILed:
    def __init__(self, logger):
        self.logger = logger
        
        self.ledbar = [None for x in range(10)]
        
        self.frame = None
        
        self.lower_bound = [5000 for x in range(11)]
        self.shiftrpm = [7000 for x in range(11)]
        
        self.step = [(self.shiftrpm[x] - self.lower_bound[x])/4 for x in range(11)]
        
        self.state = 0
        self.rpm = 0
        
        self.lower_bound_var = tkinter.StringVar()
        self.lower_bound_var.set("0000")
        
        self.step_var = tkinter.StringVar()
        self.step_var.set("0000")
        
        self.rpm_var = tkinter.StringVar()
        self.rpm_var.set("0000")

    def timeadjusted_rpm(self, framecount, rpm_start, rpmvalues):
        for j, x in enumerate(rpmvalues):
            if x >= rpm_start:
                offset = int(max(j - framecount, 0))
                return int(rpmvalues[offset])
                #print(f"j {j} val {rpmvalues[j]} offset {offset}")
        return int(rpmvalues[-framecount-1]) #if rpm_start not in rpmvalues, commonly used for revlimit

    def set_rpmtable(self, rpmtable, rpmvalues, gears, revlimit, collectedingear, trace):
        self.logger.info(f"revlimit {revlimit} collectedingear {collectedingear}")
        for gear, rpm in enumerate(rpmtable):
            if rpm == 0: #rpmtable has initial 0 and 0 for untested gears
                continue
            
            self.logger.info(f"gear {gear} rpm {rpm}")
            
            scalar = gears[gear-1] / gears[collectedingear-1]
            self.logger.info(f"scalar is {scalar}")
            
            #if at rev limit within 80 milliseconds, shift optimal shift point state to be 80 milliseconds away
            #scale this to include scalar variable
            effective_frames_to_revlimit = math.ceil(DISTANCE_FROM_REVLIMIT*scalar)
            adjusted_rpmlimit = int(self.timeadjusted_rpm(effective_frames_to_revlimit, revlimit, rpmvalues))
            self.logger.info(f"adjusted rpmlimit {adjusted_rpmlimit}")
            
            rpm = min(rpm, adjusted_rpmlimit)
            
            for j, x in enumerate(rpmvalues):
                if x >= rpm:
                    offset = int(max(j - scalar*ILLUMINATION_INTERVAL, 0))
                    self.lower_bound[gear] = int(rpmvalues[offset])
                    #print(f"j {j} val {rpmvalues[j]} offset {offset}")
                    break
                
            self.shiftrpm[gear] = rpm
            self.step[gear] = (self.shiftrpm[gear] - self.lower_bound[gear])/4
            self.logger.info(f"gear {gear} newshiftrpm {self.shiftrpm[gear]} "
                             f"start {self.lower_bound[gear]} step {self.step[gear]}")
        
    def update (self, fdp):
        state = math.ceil((fdp.current_engine_rpm - self.lower_bound[fdp.gear]) / self.step[fdp.gear])
        if state < 0:
            state = 0
        if state > 6:
            state = 6
            
        self.lower_bound_var.set(f"{self.lower_bound[fdp.gear]}")
        self.step_var.set(f"{self.step[fdp.gear]}")
        self.rpm_var.set(f"{fdp.current_engine_rpm:.0f}")
                    
        self.update_leds()
        self.state = state

    def update_leds(self):
        ledbar = STATES[self.state]
        for i in range(10):
            self.frame.itemconfig(self.ledbar[i], fill=ledbar[i])
    
    def set_canvas(self, frame):
        self.frame = tkinter.Canvas(frame, border=0, bg=constants.background_color, relief="groove",
                                            highlightthickness=True, highlightcolor=constants.text_color)

        tkinter.Label(self.frame, text="LED gearshifts", bg=constants.background_color, fg=constants.text_color,
                      font=('Helvetica 15 bold')).place(relx=0.2, rely=0.2, anchor=tkinter.CENTER)
        tkinter.Label(self.frame, textvariable=self.lower_bound_var, bg=constants.background_color, fg=constants.text_color,
                      font=('Helvetica 15 bold')).place(relx=0.5, rely=0.2, anchor=tkinter.CENTER)
        tkinter.Label(self.frame, textvariable=self.step_var, bg=constants.background_color, fg=constants.text_color,
                      font=('Helvetica 15 bold')).place(relx=0.8, rely=0.2, anchor=tkinter.CENTER)
        tkinter.Label(self.frame, textvariable=self.rpm_var, bg=constants.background_color, fg=constants.text_color,
                      font=('Helvetica 15 bold')).place(relx=0.8, rely=0.6, anchor=tkinter.CENTER)
        
        for i in range(10):
            self.ledbar[i] = self.frame.create_rectangle(10+30* i, 40,10+30+30* i,40+30, fill='black', outline='white')
    
    def reset(self):
        self.state = 0
        self.update_leds()
        
        self.lower_bound_var.set("0000")
        self.step_var.set("0000")
        self.rpm_var.set("0000")
        
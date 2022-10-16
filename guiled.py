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
    #test hysteresis value
    #create separate window for the shift lights, force it on top
    #self.root.wm_attributes("-topmost", 1) #put window on top, over forza
    
    #blank shift leds after detecting gear change
    #gear change is a gradual process in telemetry: power is cut (negative), then gear changes, then power goes positive again
    #blank on gear variable changing is simplest, but can be very slow
    #we can use inputs: https://pypi.org/project/inputs/0.3/
    #or https://gist.github.com/artizirk/b407ba86feb7f0227654f8f5f1541413
    #or https://github.com/bayangan1991/PYXInput

BLACK = '#000000'
GREEN = '#80FF80'
AMBER = '#FFBF7F'
RED   = '#FF8088'
BLUE  = '#8080FF'

ILLUMINATION_INTERVAL = int(2.0*60) #2.0 seconds
REACTION_TIME = 12 #200 milliseconds
DISTANCE_FROM_REVLIMIT_MS = 5 #83 milliseconds
DISTANCE_FROM_REVLIMIT_ABS = .99 #99.2% of rev limit
HYSTERESIS_PCT_REVLIMIT = 0.001 #0.1% of rev limit
COUNTDOWN_MAX = 12 #dropping state only allowed after 12 frames

STATES = [
    [BLACK]*10,
    [GREEN, GREEN] + [BLACK]*8,
    [GREEN, GREEN, AMBER, AMBER] + [BLACK]*6,
    [GREEN, GREEN, AMBER, AMBER, AMBER, AMBER, ] + [BLACK]*4,
    [GREEN, GREEN, AMBER, AMBER, AMBER, AMBER, RED, RED] + [BLACK]*2,
    [BLUE]*10,
    [RED, BLUE, RED, BLUE, RED, RED, BLUE, RED, BLUE, RED] ]

class GUILedDummy:
    def __init__(self, logger, root):
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
    def __init__(self, logger, root):
        self.logger = logger
        
        self.ledbar = [None for x in range(10)]
        
        self.frame = None
        
        self.run_shiftleds = [True for x in range(11)]
        self.lower_bound = [5000 for x in range(11)]
        self.shiftrpm = [7000 for x in range(11)]
        self.unhappy_rpm = [7500 for x in range(11)]
        self.hysteresis_rpm = HYSTERESIS_PCT_REVLIMIT*7500
        
        self.step = [(self.shiftrpm[x] - self.lower_bound[x])/4 for x in range(11)]
        
        self.state = 0
        self.rpm = 0
        self.statedowntimer = 0
        
        # self.lower_bound_var = tkinter.StringVar()
        # self.lower_bound_var.set("0000")
        
        # self.step_var = tkinter.StringVar()
        # self.step_var.set("0000")
        
        self.rpm_var = tkinter.StringVar()
        self.rpm_var.set("0000")
        
        self.__init__window(root)
            
    def __init__window(self, root):
            START_X = 0
            START_Y = 0
            LED_HEIGHT = 40
            LED_WIDTH = 40
            LED_COUNT = 10
            self.root = root
            self.window = tkinter.Toplevel(root)
            self.window.wm_attributes("-topmost", 1)
            height = LED_HEIGHT
            width = LED_WIDTH*LED_COUNT
            self.window.geometry(f"{width}x{height}+0+0")
            self.canvas = tkinter.Canvas(self.window, width=width, height=height, bg=constants.background_color)
            self.canvas.pack()
            #self.window.overrideredirect(True) #remove title bar, needs code to allow window to move
           
            for i in range(LED_COUNT):
                # self.ledbar[i] = self.canvas.create_rectangle(START_X,           START_Y+LED_HEIGHT*i, 
                #                                              START_X+LED_WIDTH, START_Y+LED_HEIGHT*(i+1), 
                #                                              fill='black', outline='white')
                self.ledbar[i] = self.canvas.create_rectangle(START_X+LED_WIDTH*i, START_Y,
                                                         START_X+LED_WIDTH*(i+1),START_Y+LED_HEIGHT, 
                                                         fill='black', outline='white')
            #self.ledbar[i] = self.frame.create_rectangle(10+30*i, 40,10+30+30*i,40+30, fill='black', outline='white')

    def timeadjusted_rpm(self, framecount, rpm_start, rpmvalues):
        for j, x in enumerate(rpmvalues):
            if x >= rpm_start:
                offset = int(max(j - framecount, 0))
                return int(rpmvalues[offset])
                #print(f"j {j} val {rpmvalues[j]} offset {offset}")
        return int(rpmvalues[-framecount-1]) #if rpm_start not in rpmvalues, commonly used for revlimit

    def set_rpmtable(self, rpmtable, rpmvalues, gears, revlimit, collectedingear, trace):
        self.logger.info(f"revlimit {revlimit} collectedingear {collectedingear}")
        
        self.hysteresis_rpm = HYSTERESIS_PCT_REVLIMIT*revlimit
        self.logger.info(f"hysteresis at {self.hysteresis_rpm} rpm steps")
        
        drag = DragDerivation(gears, final_drive=1, trace=trace)
        geardata = DragDerivation.derive_timespeed_all_gears(**drag.__dict__)
        
        lim = int(len(trace.rpm)/10) #find close fitting ratio for rpm/speed based on the last 10% of the sweep
        rpmspeedratio = np.average(trace.rpm[-lim:] / trace.speed[-lim:])
        gearratio_collected = gears[collectedingear-1]
        
        #data['rpm'] is the drag corrected rpm over time per gear
        for data, gearratio in zip(geardata[1:], gears):
            data['rpm'] = data['speed'] * (gearratio / gearratio_collected) * rpmspeedratio
        
        for gear, rpm in enumerate(rpmtable):
            if rpm == 0: #rpmtable has initial 0 and 0 for untested gears
                continue
            self.run_shiftleds[gear] = True
            
            self.logger.info(f"gear {gear} rpm {rpm}")
            
            #if at rev limit within x milliseconds, shift optimal shift point state to be x milliseconds away
            adjusted_rpmlimit_ms = self.timeadjusted_rpm(DISTANCE_FROM_REVLIMIT_MS, revlimit, geardata[gear]['rpm'])
            adjusted_rpmlimit_abs = int(revlimit*DISTANCE_FROM_REVLIMIT_ABS)
            self.logger.info(f"adjusted rpmlimit ms:{adjusted_rpmlimit_ms}, abs: {adjusted_rpmlimit_abs}")
            
            rpm = min(rpm, adjusted_rpmlimit_ms, adjusted_rpmlimit_abs)
            
            #at optimal shift rpm, we change state to 'past optimal' because humans have reaction time
            self.unhappy_rpm[gear] = rpm
            rpm = self.timeadjusted_rpm(REACTION_TIME, rpm, geardata[gear]['rpm'])
            self.logger.info(f"adjusted for reaction time {rpm}")
            
            for j, x in enumerate(geardata[gear]['rpm']):
                if x >= rpm:
                    offset = int(max(j - ILLUMINATION_INTERVAL, 0))
                    self.lower_bound[gear] = int(geardata[gear]['rpm'][offset])
                    #print(f"j {j} val {rpmvalues[j]} offset {offset}")
                    break
                
            self.shiftrpm[gear] = rpm
            self.step[gear] = (self.shiftrpm[gear] - self.lower_bound[gear])/4
            self.logger.info(f"gear {gear} newshiftrpm {self.shiftrpm[gear]} "
                             f"start {self.lower_bound[gear]} step {self.step[gear]}")
        
    def update (self, fdp):
        self.rpm_var.set(f"{fdp.current_engine_rpm:.0f}")
        
        if not self.run_shiftleds[fdp.gear]:
            return
        
        if abs(self.rpm - fdp.current_engine_rpm) >= self.hysteresis_rpm:
            self.rpm = fdp.current_engine_rpm
        state = math.ceil((self.rpm - self.lower_bound[fdp.gear]) / self.step[fdp.gear])
        if self.rpm > self.unhappy_rpm[fdp.gear]:
            state = 6
        
        if state < 0:
            state = 0
        if state > 6:
            state = 6
            
        if state < self.state:
            if self.countdowntimer < COUNTDOWN_MAX:
                self.countdowntimer += 1
            else:
                self.state = state
        else:
            self.countdowntimer = COUNTDOWN_MAX
            self.state = state
            
        # self.lower_bound_var.set(f"{self.lower_bound[fdp.gear]}")
        # self.step_var.set(f"{self.step[fdp.gear]}")
                    
        self.update_leds()

    def update_leds(self):
        ledbar = STATES[self.state]
        for i in range(10):
            self.canvas.itemconfig(self.ledbar[i], fill=ledbar[i])

    def set_canvas(self, frame):
        self.frame = tkinter.Canvas(frame, border=0, bg=constants.background_color, relief="groove",
                                            highlightthickness=True, highlightcolor=constants.text_color)

        # tkinter.Label(self.frame, text="LED gearshifts", bg=constants.background_color, fg=constants.text_color,
        #               font=('Helvetica 15 bold')).place(relx=0.2, rely=0.2, anchor=tkinter.CENTER)
        # tkinter.Label(self.frame, textvariable=self.lower_bound_var, bg=constants.background_color, fg=constants.text_color,
        #               font=('Helvetica 15 bold')).place(relx=0.5, rely=0.2, anchor=tkinter.CENTER)
        # tkinter.Label(self.frame, textvariable=self.step_var, bg=constants.background_color, fg=constants.text_color,
        #               font=('Helvetica 15 bold')).place(relx=0.8, rely=0.2, anchor=tkinter.CENTER)
        tkinter.Label(self.frame, textvariable=self.rpm_var, bg=constants.background_color, fg=constants.text_color,
                      font=('Helvetica 18 bold')).place(relx=0.8, rely=0.9, anchor=tkinter.CENTER)
        
        # START_X = 250-80
        # START_Y = 1
        # LED_HEIGHT = 45
        # LED_WIDTH = 80
        # for i in range(10):
        #     self.ledbar[i] = self.frame.create_rectangle(START_X,           START_Y+LED_HEIGHT*i, 
        #                                                  START_X+LED_WIDTH, START_Y+LED_HEIGHT*(i+1), 
        #                                                  fill='black', outline='white')
        self.frame.pack(fill='both', expand=True)
            #self.ledbar[i] = self.frame.create_rectangle(40, 1+45*i, 40+80, 1+50+45*i, fill='black', outline='white')
            #self.ledbar[i] = self.frame.create_rectangle(10+30*i, 40,10+30+30*i,40+30, fill='black', outline='white')
    
    def reset(self):
        self.state = 0
        self.dropdowntimer = COUNTDOWN_MAX
        self.update_leds()
        
        # self.lower_bound_var.set("0000")
        # self.step_var.set("0000")
        self.rpm_var.set("0000")
        
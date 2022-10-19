# -*- coding: utf-8 -*-
"""
Created on Sun Feb 13 15:16:10 2022

@author: RTB
"""

import tkinter
import tkinter.ttk
import constants
import math
#import matplotlib.pyplot as plt
import numpy as np

from dragderivation import Trace, DragDerivation

#TODO:
    #test hysteresis value
    #create configuration file for constants
    #add frame to gui to edit constants in real time
    #move constants into objects
        #name, value, gui_var, text, posttext, from/to lambdas
        #rewrite state triggers to use a full table
            #add full state trigger table to gui
        #dynamic led sizing?
    #add audio tone to (different) reaction time adjusted shift rpm
            
        
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

STATES = [
    [BLACK]*10,
    [GREEN, GREEN] + [BLACK]*8,
    [GREEN, GREEN, AMBER, AMBER] + [BLACK]*6,
    [GREEN, GREEN, AMBER, AMBER, AMBER, AMBER, ] + [BLACK]*4,
    [GREEN, GREEN, AMBER, AMBER, AMBER, AMBER, RED, RED] + [BLACK]*2,
    [BLUE]*10,
    [RED, BLUE, RED, BLUE, RED, RED, BLUE, RED, BLUE, RED] ]

START_X = 0
START_Y = 0
LED_HEIGHT = 75
LED_WIDTH = 75
LED_COUNT = 10
HEIGHT = LED_HEIGHT
WIDTH = LED_WIDTH*LED_COUNT

#extend tkinter.Variable? get and set functions are only set for the subtypes
class Variable():
    def __init__(self, name, defaultvalue, vartype, unit):
        self.name = name
        self.defaultvalue = defaultvalue
        self.vartype = vartype
        self.unit = unit
        
    def get(self):
        return self.var.get()
    
    def set(self, value):
        return self.var.set(value)

    def init_tkintervar(self):
        if self.vartype == 'String':
            self.var = tkinter.StringVar(value=self.defaultvalue)
        elif self.vartype == 'Double':
            self.var = tkinter.DoubleVar(value=self.defaultvalue)
        elif self.vartype == 'Int':
            self.var = tkinter.IntVar(value=self.defaultvalue)
        
#convenient class for displaying and modifying variables live in the GUI
class V(): 
    illumination_interval = Variable('Illumination interval', int(2.0*60), 'Int', 'frames')  #2.0 seconds
    reaction_time = Variable('Reaction time', 12, 'Int', 'frames')  #200 milliseconds
    distance_from_revlimit_ms = Variable('Distance from revlimit', 5, 'Int', 'frames')  #83 milliseconds
    distance_from_revlimit_pct = Variable('Distance from revlimit', .99, 'Double', 'percent')  #99.0% of rev limit
    hysteresis_pct_revlimit = Variable('Hysteresis downwards', .001, 'Double', 'percent') #0.1% of rev limit
    state_dropdown_delay = Variable('State dropdown delay', 12, 'Int', 'frames')  #dropping state only allowed after 12 frames
    shiftlight_x = Variable('Shiftlight location x', 1532, 'Int', 'pixels')
    shiftlight_y = Variable('Shiftlight location y', 1763, 'Int', 'pixels')
    
    #initialize tkinter variable must be done after creating a tkinter root window
    @classmethod 
    def _init_tkintervariables(cls):
        for name, value in cls.__dict__.items():
            if name[0] == '_':
                continue
            value.init_tkintervar()
    
    @classmethod
    def _var_list(cls):
        return [var for name, var in cls.__dict__.items() if name[0] != '_']

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
        
        self.run_shiftleds = [False for x in range(11)]
        self.lower_bound = [5000 for x in range(11)] #these placeholder values mean nothing
        self.shiftrpm = [7000 for x in range(11)]
        self.unhappy_rpm = [7500 for x in range(11)]
        self.hysteresis_rpm = V.hysteresis_pct_revlimit.defaultvalue*7500
        
        self.step = [(self.shiftrpm[x] - self.lower_bound[x])/4 for x in range(11)]
        
        self.state = 0
        self.rpm = 0
        self.statedowntimer = 0
        
        self.update_rpm_var = True
        self.rpm_var = tkinter.StringVar(value='0000')
        
        self.state_table = [[0 for x in range(0, len(STATES))] for y in range(11)]
                    
        self.__init__window(root)
        V._init_tkintervariables()
            
    def __init__window(self, root):
            self.root = root
            self.window = tkinter.Toplevel(root)
            self.window.wm_attributes("-topmost", 1) #force always on top
            self.window.geometry(f"{WIDTH}x{HEIGHT}+{V.shiftlight_x.defaultvalue}+{V.shiftlight_y.defaultvalue}")
            self.canvas = tkinter.Canvas(self.window, width=WIDTH, height=HEIGHT, bg="#000000")
            self.canvas.pack()
            self.window.overrideredirect(True) #remove title bar, needs code to allow window to move
           
            for i in range(LED_COUNT):
                self.ledbar[i] = self.canvas.create_rectangle(START_X+LED_WIDTH*i, START_Y,
                                                         START_X+LED_WIDTH*(i+1),START_Y+LED_HEIGHT, 
                                                         fill='black', outline='white')
                
                #vertical bar, remember to swap *LED_COUNT from WIDTH to HEIGHT 
                # self.ledbar[i] = self.canvas.create_rectangle(START_X,           START_Y+LED_HEIGHT*i, 
                #                                              START_X+LED_WIDTH, START_Y+LED_HEIGHT*(i+1), 
                #                                              fill='black', outline='white')
            
            #from https://stackoverflow.com/questions/4055267/tkinter-mouse-drag-a-window-without-borders-eg-overridedirect1
            self.canvas.bind("<ButtonPress-1>", self.start_move)
            self.canvas.bind("<ButtonRelease-1>", self.stop_move)
            self.canvas.bind("<B1-Motion>", self.do_move)

    def start_move(self, event):
        self.x = event.x
        self.y = event.y

    def stop_move(self, event):
        deltax = event.x - self.x
        deltay = event.y - self.y
        V.shiftlight_x.set(self.window.winfo_x() + deltax)
        V.shiftlight_y.set(self.window.winfo_y() + deltay)
        self.logger.info(f"ledbar offset {V.shiftlight_x.get()} and {V.shiftlight_y.get()}")
        self.x = None
        self.y = None

    def do_move(self, event):
        deltax = event.x - self.x
        deltay = event.y - self.y
        x = self.window.winfo_x() + deltax
        y = self.window.winfo_y() + deltay
        self.window.geometry(f"+{x}+{y}")

    def timeadjusted_rpm(self, framecount, rpm_start, rpmvalues):
        for j, x in enumerate(rpmvalues):
            if x >= rpm_start:
                offset = int(max(j - framecount, 0))
                return int(rpmvalues[offset])
                #print(f"j {j} val {rpmvalues[j]} offset {offset}")
        return int(rpmvalues[-framecount-1]) #if rpm_start not in rpmvalues, commonly used for revlimit

    #TODO: remove unused variables: rpmvalues and collectedingear
    def set_rpmtable(self, rpmtable, rpmvalues, gears, revlimit, collectedingear, trace):
        self.logger.info(f"revlimit {revlimit} gear_collected {trace.gear_collected}")
        
        self.rpmtable = rpmtable
        self.revlimit = revlimit
        
        drag = DragDerivation(gears, final_drive=1, trace=trace)
        self.geardata = DragDerivation.derive_timespeed_all_gears(**drag.__dict__)
        
        lim = int(len(trace.rpm)/10) #find close fitting ratio for rpm/speed based on the last 10% of the sweep
        rpmspeedratio = np.average(trace.rpm[-lim:] / trace.speed[-lim:])
        gearratio_collected = gears[trace.gear_collected-1]
        
        #data['rpm'] is the drag corrected rpm over time per gear
        for data, gearratio in zip(self.geardata[1:], gears):
            data['rpm'] = data['speed'] * (gearratio / gearratio_collected) * rpmspeedratio
            
        self.calculate_state_triggers()
    
    #TODO: remove intermediary step with lower_bound, step and shiftrpm and translate straight to state triggers
    def calculate_state_triggers(self):
        for gear, rpm in enumerate(self.rpmtable):
            if rpm == 0: #rpmtable has initial 0 and 0 for untested gears
                continue
            self.run_shiftleds[gear] = True
            
            self.logger.info(f"gear {gear} rpm {rpm}")
            
            #if at rev limit within x milliseconds, shift optimal shift point state to be x milliseconds away
            adjusted_rpmlimit_ms = self.timeadjusted_rpm(V.distance_from_revlimit_ms.get(), self.revlimit, self.geardata[gear]['rpm'])
            adjusted_rpmlimit_abs = int(self.revlimit*V.distance_from_revlimit_pct.get())
            self.logger.info(f"adjusted rpmlimit ms:{adjusted_rpmlimit_ms}, abs: {adjusted_rpmlimit_abs}")
            
            rpm = min(rpm, adjusted_rpmlimit_ms, adjusted_rpmlimit_abs)
            
            #at optimal shift rpm, we change state to 'past optimal' because humans have reaction time
            self.unhappy_rpm[gear] = rpm
            rpm = self.timeadjusted_rpm(V.reaction_time.get(), rpm, self.geardata[gear]['rpm'])
            self.logger.info(f"adjusted for reaction time {rpm}")
            
            for j, x in enumerate(self.geardata[gear]['rpm']):
                if x >= rpm:
                    offset = int(max(j - V.illumination_interval.get(), 0))
                    self.lower_bound[gear] = int(self.geardata[gear]['rpm'][offset])
                    #print(f"j {j} val {rpmvalues[j]} offset {offset}")
                    break
                
            self.shiftrpm[gear] = rpm
            self.step[gear] = (self.shiftrpm[gear] - self.lower_bound[gear])/4
         #   self.logger.info(f"gear {gear} newshiftrpm {self.shiftrpm[gear]} "
         #                    f"start {self.lower_bound[gear]} step {self.step[gear]}")
            
            gear_table = self.state_table[gear]
            for x in range(1,5):
                gear_table[x] = int(self.lower_bound[gear] + self.step[gear]*(x-1))
            gear_table[5] = self.shiftrpm[gear] #happy state
            gear_table[6] = self.unhappy_rpm[gear] #unhappy state
            
            self.logger.info(gear_table)
        
        self.hysteresis_rpm = V.hysteresis_pct_revlimit.get()*self.revlimit
        self.logger.info(f"hysteresis downwards at {self.hysteresis_rpm} rpm steps")

    def update_button(self, event):
        if (V.shiftlight_x.get() != self.window.winfo_x() or V.shiftlight_y.get() != self.window.winfo_y()):
            self.window.geometry(f"+{V.shiftlight_x.get()}+{V.shiftlight_y.get()}")
            self.logger.info(f"ledbar offset {V.shiftlight_x.get()} and {V.shiftlight_y.get()}")
        else:
            self.calculate_state_triggers()
        self.logger.info("update button hit!")

    def update (self, fdp):
        if self.update_rpm_var:
            self.rpm_var.set(f"{fdp.current_engine_rpm:.0f} {self.rpm:.0f}")
        self.update_rpm_var = not(self.update_rpm_var)
        
        if not self.run_shiftleds[fdp.gear]:
            return
        
        #if engine rpm is dropping, do not drop corrected rpm until difference drops below hysteresis value
        if (fdp.current_engine_rpm - self.rpm <= -self.hysteresis_rpm or
            fdp.current_engine_rpm - self.rpm >= 0):
            self.rpm = fdp.current_engine_rpm
        
        #loop over state triggers in reverse order
        for state, shiftrpm in reversed(list(enumerate(self.state_table[fdp.gear]))):
            if self.rpm > shiftrpm:
                break
            
        if state < self.state:
            if self.countdowntimer < V.state_dropdown_delay.get():
                self.countdowntimer += 1
            else:
                self.state = state
        else:
            self.countdowntimer = V.state_dropdown_delay.get()
            self.state = state
                                
        self.update_leds()

    def update_leds(self):
        ledbar = STATES[self.state]
        for i in range(10):
            self.canvas.itemconfig(self.ledbar[i], fill=ledbar[i])

    def set_canvas(self, frame):
        self.frame = tkinter.Frame(frame, border=0, bg=constants.background_color, relief="groove",
                                            highlightthickness=True, highlightcolor=constants.text_color)
        
        opts = {'bg':constants.background_color, 'fg':constants.text_color, 'font':('Helvetica 12')}
        
        for row, v in enumerate(V._var_list()):
            tkinter.Label(self.frame, text=v.name, **opts).grid(row=row, column=0)
            tkinter.Entry(self.frame, textvariable=v.var, width=5, justify=tkinter.RIGHT, **opts).grid(row=row, column=1)
            tkinter.Label(self.frame, text=v.unit, **opts).grid(row=row, column=2)            
            
        tkinter.Label(self.frame, textvariable=self.rpm_var, bg=constants.background_color, fg=constants.text_color,
                      font=('Helvetica 18 bold')).grid(row=row+1)

        #TODO: grey out update button unless changes are made?
        button = tkinter.Button(self.frame, text='Update', bg=constants.background_color, fg=constants.text_color,
                                borderwidth=3, highlightcolor=constants.text_color, highlightthickness=True)
        button.bind('<Button-1>', self.update_button)
        button.grid(row=row+1, column=1, columnspan=2)

        self.frame.pack(fill='both', expand=True)
    
    def reset(self):
        self.state = 0
        self.dropdowntimer = V.state_dropdown_delay.get()
        self.update_leds()
        
        # self.lower_bound_var.set("0000")
        # self.step_var.set("0000")
        self.update_rpm_var = True
        self.rpm_var.set("0000")
        

        
        
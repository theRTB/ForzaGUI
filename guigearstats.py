# -*- coding: utf-8 -*-
"""
Created on Wed Jun 15 10:37:54 2022

@author: RTB
"""

import tkinter
import tkinter.ttk

from collections import deque
import statistics

import constants
import math

from fdp import ForzaDataPacketDeque

MAXGEARS = 10
GEARLIST = range(MAXGEARS+1)
GEARLABELS = ['R'] + list(GEARLIST[1:]) #R,1,2,3,4,5,6,7,8,9,10
'''
TODO:
    - update shiftdelay to be more accurate
    - a full shift is longer than the distance between 


    - add option to hide unused gears for known cars through greying out rows
    - add clutch display given known gear ratios for cars where the ratio doesn't float
'''

class GearRow():
    def __init__(self, gear):
        self.gear = gear #TODO:necessary?
        self.label = GEARLABELS[gear]
        self.ratio = 0 #separate to force an output format of 2.3f in GUI
        self.ratio_var = tkinter.StringVar()
        self.shiftrpm = tkinter.IntVar()
        self.lastshiftrpm = tkinter.IntVar() #TODO: extend to deque?
        
        self.reset()

    def get_label(self):
        return self.label.get()
    
    def get_gearratio(self):
        return self.ratio
    
    def get_shiftrpm(self):
        return self.shiftrpm.get()
    
    def get_lastshiftrpm(self):
        return self.lastshiftrpm.get()
    
    def set_gearratio(self, val):
        self.ratio = val
        self.ratio_var.set(f'{val:2.3f}')
    
    def set_shiftrpm(self, val):
        self.shiftrpm.set(int(round(val, 0)))
    
    def set_lastshiftrpm(self, val):
        self.lastshiftrpm.set(int(round(val, 0)))

    def set_canvas(self, frame, opts):
        grid = {'row':self.gear+1, 'sticky':tkinter.EW}
        tkinter.Label(frame, text=self.label, **opts).grid(column=0, **grid)
        tkinter.Label(frame, textvariable=self.ratio_var, width=5, **opts).grid(column=1, **grid)
        tkinter.Label(frame, textvariable=self.shiftrpm, **opts).grid(column=2, **grid)
        tkinter.Label(frame, textvariable=self.lastshiftrpm, **opts).grid(column=3, **grid)

    def reset(self):
        self.set_gearratio(0)
        if self.gear in [0, 10]:
            self.shiftrpm.set('-')
            self.lastshiftrpm.set('-')
        else:
            self.set_shiftrpm(0)
            self.set_lastshiftrpm(0)
            
class GearTable():
    FIRSTROW = ['Gear', 'Ratio', 'Optimal\nshiftrpm', 'Last\nshiftrpm']
    def __init__(self):
        self.rows = [GearRow(gear) for gear in GEARLIST]
    
    def set_gearratio(self, gear, ratio):
        self.rows[gear].set_gearratio(ratio)
        
    def set_lastshiftrpm(self, gear, rpm):
        self.rows[gear].set_lastshiftrpm(rpm)
        
    def get_gearratios(self):
        return [row.get_gearratio() for row in self.rows]    
    
    def set_gearratios(self, array):
        for row, ratio in zip(self.rows, array):
            row.set_gearratio(ratio)

    def get_shiftrpms(self):
        return [row.get_shiftrpm() for row in self.rows]

    def set_shiftrpms(self, array):
        for row, ratio in zip(self.rows, array):
            row.set_shiftrpm(ratio)

    def set_canvas(self, frame):
        self.frame = tkinter.Frame(frame, border=0, bg=constants.background_color, relief="groove",
                                            highlightthickness=True, highlightcolor=constants.text_color)
        
        opts = {'bg':constants.background_color, 'fg':constants.text_color,
                'font':('Helvetica 11 bold'), 'relief':tkinter.SUNKEN}        
        for column, name in enumerate(self.FIRSTROW):
            tkinter.Label(self.frame, text=name, **opts).grid(row=0, column=column, sticky=tkinter.NSEW)
            self.frame.columnconfigure(column, weight=1)
        
        opts.update({'font':('Helvetica 11'), 'justify': tkinter.RIGHT, 'anchor':tkinter.E}) #the sticky EW should override anchor E?
        for row in self.rows:
            row.set_canvas(self.frame, opts)
        
    def reset(self):
        for row in self.rows:
            row.reset()

class GUIGearStats:
    deque_attributes = []
    def __init__(self, logger, *args, **kwargs):
        self.logger = logger
        
        self.gatherratios = False
        
        self.deque = deque(maxlen=120)
        self.table = GearTable()
        
        self.shiftdelay_var = tkinter.StringVar()
        self.shiftdelay_median = 0
        self.shiftdelay_latest = 0
        self.shiftdelay = deque(maxlen=20)
        self.shiftdelay_step = 0
        self.shiftdelay_gear = 0
        self.shiftdelay_rpm = 0
        self.shiftdelay_counter = 0
        
        self.gear = 1
        self.gear_var = tkinter.StringVar()
        
        self.reset()
        
    def display(self):
        gear = self.gear if self.gear > 0 else 'R'
        self.gear_var.set(f'Gear: {gear}')
        self.shiftdelay_var.set(f'Shiftdelay: {self.shiftdelay_latest/60:.2f}s {self.shiftdelay_median/60:.2f}s')

    #return array of 11 elements: R, 1 to 10. R is generally 0
    #currently, other code may assume R is guaranteed 0
    def get_gearratios(self):
        return self.table.get_gearratios()

    #if array is stripped of empty gears, fill back up
    #assume R and higher gears are empty
    def set_gearratios(self, array):
        if len(array) < len(GEARLIST):
            array = [0] + array + [0]*(MAXGEARS - len(array))
        self.table.set_gearratios(array)
    
    #returns an array stripped of gear R and unused gears
    def get_shiftrpms(self):
        return [rpm for rpm in self.table.get_shiftrpms() if rpm != 0]

    #if array is stripped of empty gears, fill back up
    #assume R and higher gears are empty
    def set_shiftrpms(self, array):
        if len(array) < len(GEARLIST):
            array = [0] + array + [0]*(MAXGEARS - len(array))
        self.table.set_shiftrpms(array)

    #//Corresponds to EDrivetrainType; 0 = FWD, 1 = RWD, 2 = AWD
    #NOTE: ratio is off by relative front/back size if AWD conversion and front/rear are different sizes
    def update_gearratios(self, fdp):
        rad = 0
        if abs(fdp.speed) < 2: #if speed below 2 m/s assume faulty data
            return
                
        if fdp.drivetrain_type == 0: #FWD
            rad = (fdp.wheel_rotation_speed_FL + fdp.wheel_rotation_speed_FR) / 2.0
        elif fdp.drivetrain_type == 1: #RWD
            rad = (fdp.wheel_rotation_speed_RL + fdp.wheel_rotation_speed_RR) / 2.0
        else:
            #rad = (fdp.wheel_rotation_speed_RL + fdp.wheel_rotation_speed_RR) / 2.0
            rad = (fdp.wheel_rotation_speed_FL + fdp.wheel_rotation_speed_FR + 
                   fdp.wheel_rotation_speed_RL + fdp.wheel_rotation_speed_RR) / 4.0
        if abs(rad) <= 1e-6:
            return
        # if rad < 0: #in the case of reverse
        #     rad = -rad
        self.deque.append(2 * math.pi * fdp.current_engine_rpm / (rad * 60))
        ratio = statistics.median(self.deque)
        self.table.set_gearratio(fdp.gear, ratio)

    #TODO: update: 
    def update_car_info_shiftdelay(self, fdp):
        if fdp.accel <= 0:
            self.shiftdelay_step = 0
            return
        #fdp.accel > 0:
        if self.shiftdelay_step == 0:
            if fdp.power > 0:
                self.shiftdelay_gear = fdp.gear
                self.shiftdelay_rpm = fdp.current_engine_rpm
                self.shiftdelay_counter = 0
            elif fdp.power < 0:
                self.shiftdelay_step = 1
        
        if self.shiftdelay_step == 1:
            if fdp.power < 0:
                if fdp.gear == self.shiftdelay_gear:
                    self.shiftdelay_counter += 1
                if fdp.gear == self.shiftdelay_gear+1:
                    self.shiftdelay_step = 2
            else:
                self.shiftdelay_step = 0
        
        if self.shiftdelay_step == 2:
            if fdp.power < 0:
                self.shiftdelay_counter += 1
            elif fdp.power > 0:
                self.table.set_lastshiftrpm(self.shiftdelay_gear, self.shiftdelay_rpm)
                self.shiftdelay.append(self.shiftdelay_counter)
                self.shiftdelay_latest = self.shiftdelay_counter
                self.shiftdelay_median = statistics.median(self.shiftdelay)
                self.shiftdelay_step = 0
            else:
                self.shiftdelay_step = 0

    def update(self, fdp):
        if fdp.is_race_on == 0:
            return
        
        if self.gatherratios:
            if self.gear != fdp.gear:
                self.deque.clear()
            self.update_gearratios(fdp)
            
        self.gear = fdp.gear
        
        self.update_car_info_shiftdelay(fdp)
    
    def toggle_gatherratios(self):
        self.gatherratios = not(self.gatherratios)
        if self.gatherratios:
            self.logger.info("Updating ratios")
        else:
            self.logger.info("Ratios not updating")
    
    def set_canvas(self, frame):
        self.table.set_canvas(frame)
        self.table.frame.pack(fill='both', expand=True)
        
        tkinter.Label(frame, textvariable=self.gear_var, bg=constants.background_color, fg=constants.text_color, justify=tkinter.LEFT, width=8, 
                      font=('Helvetica 20 bold')).pack(fill='x')
        tkinter.Label(frame, textvariable=self.shiftdelay_var, bg=constants.background_color, fg=constants.text_color, justify=tkinter.LEFT, width=8, 
                      font=('Helvetica 12')).pack(fill='x')
    
    def reset(self):
        self.gear = 1
        self.shiftdelay.clear() 
        self.shiftdelay_median = 0  
        self.shiftdelay_latest = 0   
        self.shiftdelay_step = 0
        self.shiftdelay_gear = 0
        self.shiftdelay_rpm = 0
        self.shiftdelay_counter = 0
        self.counter = 0
        
        self.table.reset()
        self.deque.clear()
        
        self.display()
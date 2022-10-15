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

MAXGEARS = 10
GEARLIST = range(MAXGEARS+1)

class GUIGearStatsDummy:
    def __init__(self, logger):
        self.gatherratios = False

    def display(self):
        pass

    def get_shiftlimit (self):
        pass

    def set_rpmtable(self, rpmtable):
        pass
    
    def update(self, fdp):
        pass
    
    def set_canvas(self, frame):
        pass
    
    def reset(self):
        pass

class GUIGearStats:
    columns = ('gear','ratio', 'optimalshift', 'lastshift')
    def __init__(self, logger):
        self.logger = logger
        
        self.gatherratios = False
        self.gearratios = [0 for g in GEARLIST]
        self.gearratios_deque = [deque(maxlen=240) for x in GEARLIST]
        self.gear_tree = [0 for g in GEARLIST]
        self.counter = 0
        
        self.optimal_shiftrpm = [0 for g in GEARLIST]
        self.last_shiftrpm = [0 for g in GEARLIST]
        
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
        
        if self.counter == 60:
            self.counter = 0
            for gear in GEARLIST:
                self.treeview.item(self.gear_tree[gear], 
                                   values=(gear if gear > 0 else 'R', 
                                           round(self.gearratios[gear], 3), 
                                           int(self.optimal_shiftrpm[gear]) if gear != 0 and gear != 10 else '-', 
                                           int(self.last_shiftrpm[gear]) if gear != 0 and gear != 10 else '-'))
        else:
            self.counter += 1

    #//Corresponds to EDrivetrainType; 0 = FWD, 1 = RWD, 2 = AWD
    #NOTE: ratio is off by relative front/back size if AWD conversion and front/rear are different sizes
    def update_car_info_gear_ratios(self, fdp):
        rad = 0
        if abs(fdp.speed) < 3: 
            return
        if fdp.drivetrain_type == 0: #FWD
            rad = (fdp.wheel_rotation_speed_FL + fdp.wheel_rotation_speed_FR) / 2.0
        elif fdp.drivetrain_type == 1: #RWD
            rad = (fdp.wheel_rotation_speed_RL + fdp.wheel_rotation_speed_RR) / 2.0
        else: #AWD assumes primary power is sent to rear, otherwise gear ratio floats. 
            rad = (fdp.wheel_rotation_speed_RL + fdp.wheel_rotation_speed_RR) / 2.0
            #val = (fdp.wheel_rotation_speed_FL + fdp.wheel_rotation_speed_FR + 
             #      fdp.wheel_rotation_speed_RL + fdp.wheel_rotation_speed_RR) / 4.0
        if rad == 0:
            return
        if rad < 0: #in the case of reverse
            rad = -rad
        gear = int(fdp.gear)
        self.gearratios_deque[gear].append(2 * math.pi * fdp.current_engine_rpm / (rad * 60))
        self.gearratios[gear] = statistics.median(self.gearratios_deque[gear])

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
                self.last_shiftrpm[self.shiftdelay_gear] = self.shiftdelay_rpm
                self.shiftdelay.append(self.shiftdelay_counter)
                self.shiftdelay_latest = self.shiftdelay_counter
                self.shiftdelay_median = statistics.median(self.shiftdelay)
                self.shiftdelay_step = 0
            else:
                self.shiftdelay_step = 0
    
    def get_shiftlimit (self):
        return int(min(self.last_shiftrpm))

    def set_rpmtable (self, rpmtable):
        self.optimal_shiftrpm = [r for r in rpmtable] + [0]

    def update(self, fdp):
        self.gear = fdp.gear
        
        if self.gatherratios:
            self.update_car_info_gear_ratios(fdp)
        
        self.update_car_info_shiftdelay(fdp)
    
    def set_canvas(self, frame):   
        style = tkinter.ttk.Style()
        style.theme_use("clam")

        # set background and foreground of the treeview
        style.configure("Treeview",
                        background=constants.background_color,
                        foreground=constants.text_color,
                        fieldbackground=constants.background_color)
        style.map('Treeview', background=[('selected', '#BFBFBF')], foreground=[('selected', 'black')],
                  fieldbackground=[('selected', 'black')])
                    
        self.treeview = tkinter.ttk.Treeview(frame, columns=GUIGearStats.columns, style='Treeview', show=["headings"])
        self.treeview.heading('#0', text='\n\n')
        self.treeview.heading('gear', text='Gear', anchor=tkinter.CENTER)
        self.treeview.heading('ratio', text='Ratio', anchor=tkinter.CENTER)
        self.treeview.heading('optimalshift', text='Optimal\nshiftrpm', anchor=tkinter.CENTER)
        self.treeview.heading('lastshift', text='Last\nshiftrpm', anchor=tkinter.CENTER)
        self.treeview.column('gear', width=30, anchor=tkinter.CENTER)
        self.treeview.column('ratio', width=55, anchor=tkinter.CENTER)
        self.treeview.column('optimalshift', width=55, anchor=tkinter.CENTER)
        self.treeview.column('lastshift', width=55, anchor=tkinter.CENTER)
        
        for i in GEARLIST:
            self.gear_tree[i] = self.treeview.insert('', tkinter.END, values=('R' if i==0 else i, "-", "-", "-"))
        
        self.treeview.pack(fill="both", expand=True)
        
        tkinter.Label(frame, textvariable=self.gear_var, bg=constants.background_color, fg=constants.text_color, justify=tkinter.LEFT, width=8, 
                      font=('Helvetica 20 bold')).pack(fill='x')
        tkinter.Label(frame, textvariable=self.shiftdelay_var, bg=constants.background_color, fg=constants.text_color, justify=tkinter.LEFT, width=8, 
                      font=('Helvetica 12')).pack(fill='x')
    
    def reset(self):
        for g in GEARLIST:
            self.gearratios[g] = 0
            self.gearratios_deque[g].clear()
            self.optimal_shiftrpm[g] = 0
            self.last_shiftrpm[g] = 0
        self.gear = 1
        self.shiftdelay.clear() 
        self.shiftdelay_median = 0  
        self.shiftdelay_latest = 0   
        self.shiftdelay_step = 0
        self.shiftdelay_gear = 0
        self.shiftdelay_rpm = 0
        self.shiftdelay_counter = 0
        self.counter = 0
        
        self.display()
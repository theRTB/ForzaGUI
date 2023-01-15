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

class GUIWheelsizeDummy:
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

class GUIWheelsize:
    def __init__(self, logger):
        self.logger = logger
        
     #   self.wheelsize_var = tkinter.StringVar()
     #   self.wheelsize_var.set("00.00 00.00")
        self.wheelsize_front_var = tkinter.StringVar(value="00.00")
        self.wheelsize_rear_var = tkinter.StringVar(value="00.00")
        self.wheelsize = {'front':deque(maxlen=600), 'rear':deque(maxlen=600)}
        
        self.tracking_var = tkinter.BooleanVar(value=True)

    def display(self):
        pass
        #self.wheelsize_var.set(f"{self.wheelsize_front * 100:.2f} {self.wheelsize_rear * 100:.2f}")

    def update(self, fdp):
        if not self.tracking_var.get() or fdp.is_race_on == 0:
            return
        
        diameter = {x:0 for x in ['FL', 'FR', 'RL', 'RR']}
        
        if fdp.steer != 0 or (fdp.wheel_rotation_speed_FL == 0 or
                              fdp.wheel_rotation_speed_FR == 0 or
                              fdp.wheel_rotation_speed_RL == 0 or
                              fdp.wheel_rotation_speed_RR == 0):
            return
        
        for wheel in ['FL', 'FR', 'RL', 'RR']:
            radians = getattr(fdp, "wheel_rotation_speed_{}".format(wheel))
            diameter[wheel] = fdp.speed * 2 / radians
            
        self.wheelsize['front'].append(diameter['FL'])
        self.wheelsize['front'].append(diameter['FR'])
        self.wheelsize['rear'].append(diameter['RL'])
        self.wheelsize['rear'].append(diameter['RR'])
        
        #radius in centimeters
        self.wheelsize_front_var.set(round(statistics.median(self.wheelsize['front'])*50, 2))
        self.wheelsize_rear_var.set(round(statistics.median(self.wheelsize['rear'])*50, 2))
    
    def set_canvas(self, frame):
        self.frame = tkinter.Frame(frame, border=0, bg=constants.background_color, relief="groove",
                                   highlightthickness=True, highlightcolor=constants.text_color)
        opts = {'bg':constants.background_color, 'fg':constants.text_color, 'font':('Helvetica 13 bold')}
        row = 1
        tkinter.Label(self.frame, text='Wheel radius (cm)', **opts).grid(row=row, column=1, columnspan=2)
        
        row += 1  
        tkinter.Label(self.frame, text='Front', **opts).grid(row=row, column=1)
        tkinter.Label(self.frame, text='Rear', **opts).grid(row=row, column=2)
        
        row += 1 
        opts['font'] = ('Helvetica 18 bold')
        tkinter.Label(self.frame, textvariable=self.wheelsize_front_var, width=5, **opts).grid(row=row, column=1, sticky=tkinter.E)
        tkinter.Label(self.frame, textvariable=self.wheelsize_rear_var, width=5, **opts).grid(row=row, column=2, sticky=tkinter.E)
        
        row += 1 
        tkinter.Checkbutton(self.frame, text='Tracking', 
                            variable=self.tracking_var, 
                            bg=constants.background_color, 
                            fg=constants.text_color).grid(
                                        row=row, column=1, columnspan=2)
        
    def reset(self):
        self.wheelsize = {'front':deque(maxlen=600), 'rear':deque(maxlen=600)}
        self.wheelsize_front_var.set("00.00")
        self.wheelsize_rear_var.set("00.00")
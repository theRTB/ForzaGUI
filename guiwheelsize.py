# -*- coding: utf-8 -*-
"""
Created on Sun Feb 13 15:16:10 2022

@author: RTB
"""

import statistics
import tkinter
import tkinter.ttk

from collections import deque

import constants

class GUIWheelsize:
    WHEELSIZE_MIN = 0.05
    WHEELSIZE_MAX = 5.00
    def __init__(self, logger, *args, **kwargs):
        self.logger = logger
        
        self.front_var = tkinter.DoubleVar(value=0.00)
        self.rear_var = tkinter.DoubleVar(value=0.00)
        self.front = deque([0], maxlen=600)
        self.rear = deque([0], maxlen=600)
        
        self.tracking_var = tkinter.BooleanVar(value=True)

    def display(self):
        self.front_var.set(round(statistics.median(self.front)*100, 2))
        self.rear_var.set(round(statistics.median(self.rear)*100, 2))

    def update(self, fdp):
        if not self.tracking_var.get() or fdp.is_race_on == 0 or fdp.steer == 0:
            return
        
        for wheel in ['FL', 'FR', 'RL', 'RR']:
            rotation_speed = abs(getattr(fdp, f"wheel_rotation_speed_{wheel}"))
            if rotation_speed == 0:
                continue
            radius = fdp.speed  / rotation_speed
            if (radius < GUIWheelsize.WHEELSIZE_MIN or 
                radius > GUIWheelsize.WHEELSIZE_MAX):
                continue
            if wheel[0] == 'F':
                self.front.append(radius)
            else:
                self.rear.append(radius)
        
    def set_tracking(self, knowncar):
        self.tracking_var.set(value=knowncar)
    
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
        tkinter.Label(self.frame, textvariable=self.front_var, width=5, **opts).grid(row=row, column=1, sticky=tkinter.E)
        tkinter.Label(self.frame, textvariable=self.rear_var, width=5, **opts).grid(row=row, column=2, sticky=tkinter.E)
        
        row += 1 
        tkinter.Checkbutton(self.frame, text='Tracking', variable=self.tracking_var, 
                            bg=constants.background_color, fg=constants.text_color).grid(
                                        row=row, column=1, columnspan=2)
        
    def reset(self):
        self.front.clear()
        self.rear.clear()
        self.front.append(0)
        self.rear.append(0)
        self.front_var.set(0.00)
        self.rear_var.set(0.00)
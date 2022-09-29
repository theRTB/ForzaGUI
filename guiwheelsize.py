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
        
        self.wheelsize_var = tkinter.StringVar()
        self.wheelsize_var.set("00.00 00.00")
        self.wheelsize_front = 0
        self.wheelsize_rear = 0
        self.wheelsize = {'front':deque(maxlen=300), 'rear':deque(maxlen=300)}

    def display(self):
        self.wheelsize_var.set(f"{self.wheelsize_front * 100:.2f} {self.wheelsize_rear * 100:.2f}")

    def update(self, fdp):
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
        
        self.wheelsize_front = statistics.median(self.wheelsize['front'])
        self.wheelsize_rear = statistics.median(self.wheelsize['rear'])
    
    def set_canvas(self, frame):
        tkinter.Label(frame, text="wheelsize (cm)", bg=constants.background_color, fg=constants.text_color,
                      font=('Helvetica 15 bold')).place(relx=0.0, rely=0.8, anchor=tkinter.NW)
        tkinter.Label(frame, textvariable=self.wheelsize_var, bg=constants.background_color,
                      fg=constants.text_color, font=('Helvetica 35 bold italic')).place(relx=0.0, rely=0.85,
                                                                                        anchor=tkinter.NW)
    
    def reset(self):
        self.wheelsize = {'front':deque(maxlen=300), 'rear':deque(maxlen=300)}
        self.wheelsize_front = 0
        self.wheelsize_rear = 0
        self.wheelsize_var.set("00.00 00.00")
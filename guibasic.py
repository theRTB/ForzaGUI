# -*- coding: utf-8 -*-
"""
Created on Sun Feb 19 12:00:26 2023

@author: RTB
"""

import tkinter
import tkinter.ttk

import constants

class GUIBasic:
    def __init__(self, logger, *args, **kwargs):
        self.logger = logger

        self.acceleration_var = tkinter.StringVar()
        self.brake_var = tkinter.StringVar()
        self.steer_var = tkinter.StringVar()
        
        self.reset()

    def display(self):
        pass

    def update(self, fdp):
        self.acceleration_var.set(f"{str(round(fdp.accel / 255 * 100, 1))}%")
        self.brake_var.set(f"{str(round(fdp.brake / 255 * 100, 1))}%")
        self.steer_var.set(f"{fdp.steer}")
    
    def set_canvas(self, frame):
        self.frame = tkinter.Frame(frame, border=0, bg=constants.background_color, relief="groove",
                                   highlightthickness=True, highlightcolor=constants.text_color)

        opts = {'bg':constants.background_color, 'fg':constants.text_color}
        # place acceleration information text
        tkinter.Label(self.frame, text="Accel", font=('Helvetica 15 bold'), **opts).pack()
        tkinter.Label(self.frame, textvariable=self.acceleration_var, width=6, 
                      anchor=tkinter.E, font=('Helvetica 35 bold italic'), **opts).pack()

        # place brake information test
        tkinter.Label(self.frame, text="Brake", **opts, font=('Helvetica 15 bold')).pack()
        tkinter.Label(self.frame, textvariable=self.brake_var, width=6, 
                      anchor=tkinter.E, font=('Helvetica 35 bold italic'), **opts).pack()
        
        tkinter.Label(self.frame, text="Steer", **opts, font=('Helvetica 15 bold')).pack()
        tkinter.Label(self.frame, textvariable=self.steer_var, width=6, 
                      anchor=tkinter.E, font=('Helvetica 30 bold italic'), **opts).pack()
        
    def reset(self):
        self.acceleration_var.set("0.0%")
        self.brake_var.set("0.0%")
        self.steer_var.set("0")
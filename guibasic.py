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

        self.throttle_var = tkinter.StringVar()
        self.brake_var = tkinter.StringVar()
        self.steer_var = tkinter.StringVar()
        
        self.reset()

    def display(self):
        pass

    def update(self, fdp):
        self.throttle_var.set(f"{str(round(fdp.accel / 255 * 100, 1))}%")
        self.brake_var.set(f"{str(round(fdp.brake / 255 * 100, 1))}%")
        self.steer_var.set(f"{fdp.steer}")
    
    def tkinterLabel(self, text, variable):
        opts = {'bg':constants.background_color, 'fg':constants.text_color}
        tkinter.Label(self.frame, text=text, font=('Helvetica 15 bold'), **opts).pack()
        tkinter.Label(self.frame, textvariable=variable, width=6, 
                      anchor=tkinter.E, font=('Helvetica 25 bold italic'), **opts).pack()

    def set_canvas(self, frame):
        self.frame = tkinter.Frame(frame, border=0, bg=constants.background_color, relief="groove",
                                   highlightthickness=True, highlightcolor=constants.text_color)

        self.tkinterLabel('Throttle', self.throttle_var)
        self.tkinterLabel('Brake', self.brake_var)
        self.tkinterLabel('Steer', self.steer_var)
        
    def reset(self):
        self.throttle_var.set("0.0%")
        self.brake_var.set("0.0%")
        self.steer_var.set("0")
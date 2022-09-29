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

#'best_lap_time', 
#'last_lap_time',
#'cur_lap_time',
#'cur_race_time',
#'lap_no',

#needs updating to frame

class GUILaptimesDummy:
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

class GUILaptimes:
    def __init__(self, logger):
        self.logger = logger
        
        self.laptimes = deque(maxlen=20)
        
        self.best_lap = 0
        self.best_lap_var = tkinter.StringVar()
        self.best_lap_var.set("0.00:000")

        self.last_lap = 0
        self.last_lap_var = tkinter.StringVar()
        self.last_lap_var.set("0.00:000")
        
        self.cur_lap = 0
        self.cur_lap_var = tkinter.StringVar()
        self.cur_lap_var.set("0.00:0")
        
        self.session_time = 0
        self.session_time_var = tkinter.StringVar()
        self.session_time_var.set("0")
        
        self.current_lap = 1
        self.lap_no = 1
        self.lap_no_var = tkinter.StringVar()
        self.lap_no_var.set("1")

    def display(self):
        self.best_lap_var.set(f"{self.best_lap}")
        self.last_lap_var.set(f"{self.last_lap}")
        self.cur_lap_var.set(f"{self.cur_lap}")
        self.session_time_var.set(f"{self.session_time/60:.0f} min")
        self.lap_no_var.set(f"{self.lap_no}")

    def tolaptime(self, s):
        return f"{int(s/60):2}:{s%60:>6.3f}"
    
    def update(self, fdp):
        self.best_lap = self.tolaptime(fdp.best_lap_time)
        self.last_lap = self.tolaptime(fdp.last_lap_time)
        self.cur_lap = self.tolaptime(round(fdp.cur_lap_time,1))
        self.session_time = fdp.cur_race_time
        self.lap_no = fdp.lap_no
        
        if self.current_lap != self.lap_no:
            self.laptimes.append(self.last_lap)
            self.current_lap = self.lap_no

    
    def set_canvas(self, frame):
        tkinter.Label(frame, text="best lap", bg=constants.background_color, fg=constants.text_color,
                      font=('Helvetica 15 bold')).place(relx=0.4, rely=0.0, anchor=tkinter.NW)
        tkinter.Label(frame, textvariable=self.best_lap_var, bg=constants.background_color,
                      fg=constants.text_color, font=('Helvetica 35 bold italic')).place(relx=0.4, rely=0.05,
                                                                                        anchor=tkinter.NW)
        tkinter.Label(frame, text="last lap", bg=constants.background_color, fg=constants.text_color,
                      font=('Helvetica 15 bold')).place(relx=0.4, rely=0.2, anchor=tkinter.NW)
        tkinter.Label(frame, textvariable=self.last_lap_var, bg=constants.background_color,
                      fg=constants.text_color, font=('Helvetica 35 bold italic')).place(relx=0.4, rely=0.25,
                                                                                        anchor=tkinter.NW)
        tkinter.Label(frame, text="cur lap", bg=constants.background_color, fg=constants.text_color,
                      font=('Helvetica 15 bold')).place(relx=0.4, rely=0.4, anchor=tkinter.NW)
        tkinter.Label(frame, textvariable=self.cur_lap_var, bg=constants.background_color,
                      fg=constants.text_color, font=('Helvetica 35 bold italic')).place(relx=0.4, rely=0.45,
                                                                                        anchor=tkinter.NW)
        tkinter.Label(frame, text="session time", bg=constants.background_color, fg=constants.text_color,
                      font=('Helvetica 15 bold')).place(relx=0.4, rely=0.6, anchor=tkinter.NW)
        tkinter.Label(frame, textvariable=self.session_time_var, bg=constants.background_color,
                      fg=constants.text_color, font=('Helvetica 35 bold italic')).place(relx=0.4, rely=0.65,
                                                                                        anchor=tkinter.NW)
        tkinter.Label(frame, text="lap no", bg=constants.background_color, fg=constants.text_color,
                      font=('Helvetica 15 bold')).place(relx=0.4, rely=0.8, anchor=tkinter.NW)
        tkinter.Label(frame, textvariable=self.lap_no_var, bg=constants.background_color,
                      fg=constants.text_color, font=('Helvetica 35 bold italic')).place(relx=0.4, rely=0.85,
                                                                                        anchor=tkinter.NW)
    
    def reset(self):
        self.laptimes = []
        self.best_lap_var.set("0.00:000")
        self.last_lap_var.set("0.00:000")
        self.cur_lap_var.set("0.00:0")
        self.session_time_var.set("0 min")
        self.lap_no_var.set("0")
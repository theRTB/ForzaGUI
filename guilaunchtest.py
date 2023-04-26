# -*- coding: utf-8 -*-
"""
Created on Sat Jun 18 16:39:42 2022

@author: RTB
"""

import tkinter
import tkinter.ttk

from collections import deque
import statistics

import constants
import math
import csv

#-brake test
#- initial speed, final speed, distance

#fdp
#'dist_traveled'
#fdp.speed
#fdp.brake
#consider deriving distance with: 0.5 * start speed
    
LIMCOUNT = 3
LIMRANGE = range(LIMCOUNT)

class LaunchTest:
    def __init__ (self, start_var, end_var):
        self.start_var = tkinter.IntVar()
        self.end_var = tkinter.IntVar()
        self.time_var = tkinter.DoubleVar()
        self.time = 0
        self.initial_timestamp = 0
        self.state = GUILaunchtest.INITIAL
        
        self.reset(start_var, end_var)
        
    def reset(self, start_var, end_var):
        self.start_var.set(start_var)
        self.end_var.set(end_var)
        self.time_var.set(0)
        self.time = 0
        self.initial_timestamp = 0
        self.state = GUILaunchtest.INITIAL


class GUILaunchtest:
    INITIAL = 0
    WAIT = 1
    LAUNCH = 2
    firstrow = ['timestamp', 'accel%', 'speed', 'acceleration', 'long_g', 'slipratioFL', 'slipratioFR', 'slipratioRL', 'slipratioRR', 'startspeed', 'endspeed']
    
    DEFAULTS = [{'start_var': 0, 'end_var':97},
                {'start_var': 0, 'end_var':161},
                {'start_var': 100, 'end_var':200}]
    
    def __init__(self, logger, *args, **kwargs):
        self.logger = logger
        
        self.tests = [LaunchTest(**GUILaunchtest.DEFAULTS[x]) for x in LIMRANGE]

        self.write_var = tkinter.IntVar()
        self.write_var.set(0)
        
        self.log_var = tkinter.IntVar()
        self.log_var.set(0)
        
        #timestamp, brake%, speed, deacceleration, longtitudal g, slipratioFL/FR/RL/RR, distance
        self.launchdata = []
        
        self.reset()

    def writedata_to_csv(self):
        with open('launching.csv', 'w', newline='') as rawcsv:
            csvobject = csv.writer(rawcsv, delimiter='\t', quotechar='', quoting=csv.QUOTE_NONE)    
            csvobject.writerow(GUILaunchtest.firstrow)
            csvobject.writerows(self.launchdata)      
        self.logger.info(f"Written {len(self.launchdata)} rows to file")

    def display(self):
        for test in self.tests:
            test.time_var.set(f"{test.time/1000:.2f}")

    def get_datapoint(self, fdp, test):
        return [fdp.timestamp_ms - test.initial_timestamp, 
               fdp.accel/255.0, 
               fdp.speed,
               fdp.acceleration_z,
               fdp.acceleration_z/9.81,
               fdp.tire_slip_ratio_FL, 
               fdp.tire_slip_ratio_FR, 
               fdp.tire_slip_ratio_RL,
               fdp.tire_slip_ratio_RR,
               test.start_var.get(),
               test.end_var.get()]

    def add_datapoint(self, fdp, row):
        row = self.get_datapoint(fdp, row)
        self.launchdata.append(row)

          #  
    def update(self, fdp):
        for test in self.tests:
            # self.logger.info(f"s{test.state} {fdp.speed:.2f} {round(test.start_var.get()/3.6,2)}")
            if test.state == GUILaunchtest.INITIAL and fdp.accel == 0 and int(fdp.speed - test.start_var.get()/3.6) <= 0: #force no accel and be at or below start speed
                test.state = GUILaunchtest.WAIT
                # self.logger.info("We wait")
            elif (test.state == GUILaunchtest.WAIT and fdp.accel > 0 and fdp.brake < 1 and fdp.handbrake < 1 and 
                                            (test.start_var.get()/3.6 - fdp.speed) < 0.05): #initial launch state
                test.state = GUILaunchtest.LAUNCH
                test.initial_timestamp = fdp.timestamp_ms
                # self.logger.info(f"We launch: {test.start_var.get():.0f} -> {test.end_var.get():.0f} ({fdp.speed:.2f})")
                self.add_datapoint(fdp, test)
            elif test.state == GUILaunchtest.LAUNCH and (fdp.accel == 0 or fdp.brake > 0 or fdp.handbrake > 0): #reset state if not launching
                # self.logger.info("We reset")
                test.state = GUILaunchtest.INITIAL
            elif test.state == GUILaunchtest.LAUNCH and fdp.accel != 0 and fdp.speed < test.end_var.get()/3.6: #steady launch state
                self.add_datapoint(fdp, test)
            elif test.state == GUILaunchtest.LAUNCH and (fdp.accel != 0 or fdp.speed >= test.end_var.get()/3.6):
                test.state = GUILaunchtest.INITIAL
                test.time = fdp.timestamp_ms - test.initial_timestamp
                # test.initial_timestamp = fdp.timestamp_ms
                self.add_datapoint(fdp, test)
                
                if self.log_var.get() == 1:
                    self.logger.info(f"We launched: {test.start_var.get():.0f} -> {test.end_var.get():.0f} ({test.time:5.0f}ms)")
                
                if self.write_var.get() == 1:
                    self.writedata_to_csv()
                
                self.display()
    
    def set_canvas(self, frame):
        self.frame = tkinter.Frame(frame, border=0, bg=constants.background_color, relief="groove",
                                            highlightthickness=True, highlightcolor=constants.text_color)
        tkinter.Label(self.frame, text="Launch", bg=constants.background_color, fg=constants.text_color,
                      font=('Helvetica 15 bold')).grid(row=0, rowspan=2, columnspan=4)
        tkinter.Checkbutton(self.frame, text='Write', variable=self.write_var, bg=constants.background_color, fg=constants.text_color).grid(row=0, column=4, columnspan=2, sticky='W')
        tkinter.Checkbutton(self.frame, text='Log', variable=self.log_var, bg=constants.background_color, fg=constants.text_color).grid(row=1, column=4, columnspan=2, sticky='W')
     
        for (x, test) in enumerate(self.tests):
            tkinter.Entry(self.frame, textvariable=test.start_var, bg=constants.background_color, justify=tkinter.RIGHT, width=3,
                          fg=constants.text_color, font=('Helvetica 15 bold')).grid(row=x+2)
            tkinter.Label(self.frame, text="to", bg=constants.background_color, fg=constants.text_color,
                          font=('Helvetica 15 bold')).grid(row=x+2, column=1)
            tkinter.Entry(self.frame, textvariable=test.end_var, bg=constants.background_color,justify=tkinter.RIGHT, width=3,
                          fg=constants.text_color, font=('Helvetica 15 bold')).grid(row=x+2, column=2)
            tkinter.Label(self.frame, text=":", bg=constants.background_color, fg=constants.text_color,
                          font=('Helvetica 15 bold')).grid(row=x+2, column=3)
            tkinter.Label(self.frame, textvariable=test.time_var, bg=constants.background_color, fg=constants.text_color, width=4, justify=tkinter.RIGHT, anchor='e',
                          font=('Helvetica 15 bold')).grid(row=x+2, column=4)
            tkinter.Label(self.frame, text='s', bg=constants.background_color, fg=constants.text_color,
                          font=('Helvetica 15 bold')).grid(row=x+2, column=5)
       
      #  self.frame.place(relx=0.23, rely=0.35)
    
    def reset(self):
        for test, default in zip(self.tests, GUILaunchtest.DEFAULTS):
            test.reset(**default)
        
        self.launchdata.clear()
        
        self.display()
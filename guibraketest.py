# -*- coding: utf-8 -*-
"""
Created on Tue Jun 14 10:15:10 2022

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

class GUIBraketest:
    WAIT = 0
    BRAKE = 1
    DISPLAY = 2
    firstrow = ['timestamp', 'brake%', 'speed', 'deaccel', 'long_g', 'distance', 'slipratioFL', 'slipratioFR', 'slipratioRL', 'slipratioRR']
    
    def __init__(self, logger, *args, **kwargs):
        self.logger = logger
        self.initial_speed = 0
        self.final_speed = 0
        self.distance = 0
        self.brake_time = 0

        self.speed_var = tkinter.StringVar()
        self.distance_var = tkinter.StringVar()
        
        self.write_var = tkinter.IntVar()
        self.write_var.set(0)
        
        self.log_var = tkinter.IntVar()
        self.log_var.set(0)
        
        self.state = GUIBraketest.WAIT
        
        self.x = 0
        self.y = 0
        self.z = 0
        
        #timestamp, brake%, speed, deacceleration, longtitudal g, slipratioFL/FR/RL/RR, distance
        self.brakedata = []
        
        self.reset()

    def writedata_to_csv(self):
        with open('braking.csv', 'w', newline='') as rawcsv:
            csvobject = csv.writer(rawcsv, delimiter='\t', quotechar='', quoting=csv.QUOTE_NONE)    
            csvobject.writerow(GUIBraketest.firstrow)
            csvobject.writerows(self.brakedata)      
        self.logger.info(f"Written {len(self.brakedata)} rows to file")

    def display(self):
        self.speed_var.set(f'{self.initial_speed*3.6:6.1f} to {self.final_speed*3.6:6.1f}')
        self.distance_var.set(f'{self.distance:6.1f} ({self.brake_time:4.0f}ms)')

    def add_distance(self, x, y, z):
        self.distance += math.sqrt((x - self.x)**2 + (y - self.y)**2 + (z - self.z)**2)
        self.x = x
        self.y = y
        self.z = z

    def add_datapoint(self, fdp):
        row = [fdp.timestamp_ms - self.initial_timestamp, 
               fdp.brake/255.0, 
               fdp.speed,
               fdp.acceleration_z,
               fdp.acceleration_z/9.81,
               self.distance,
               fdp.tire_slip_ratio_FL, 
               fdp.tire_slip_ratio_FR, 
               fdp.tire_slip_ratio_RL,
               fdp.tire_slip_ratio_RR ]
        self.brakedata.append(row)

    def update(self, fdp):
        if self.state == GUIBraketest.WAIT and fdp.brake == 0 and fdp.speed > 3:
            self.initial_speed = fdp.speed
            self.x = fdp.position_x
            self.y = fdp.position_y
            self.z = fdp.position_z
        elif self.state == GUIBraketest.WAIT and fdp.brake > 0 and fdp.speed > 3: #initial braking state
            self.state = GUIBraketest.BRAKE
            self.initial_timestamp = fdp.timestamp_ms
           # self.logger.info(f"We braking {self.initial_speed*3.6:.1f}")
        if self.state == GUIBraketest.BRAKE and not (fdp.brake == 0 or fdp.speed < 0.05): #steady braking state
            self.add_distance(fdp.position_x, fdp.position_y, fdp.position_z)
            self.add_datapoint(fdp)
        elif self.state == GUIBraketest.BRAKE and (fdp.brake == 0 or fdp.speed < 0.05):
            self.final_speed = fdp.speed
            self.add_distance(fdp.position_x, fdp.position_y, fdp.position_z)
            self.add_datapoint(fdp)
            
            self.brake_time = fdp.timestamp_ms - self.initial_timestamp
            
            if self.log_var.get() == 1:
                self.logger.info(f"We braked. {self.initial_speed*3.6:.1f} {self.final_speed*3.6:.1f} {self.distance:.1f} ({self.brake_time:4.0f}ms)")
            
            if self.write_var.get() == 1:
                self.writedata_to_csv()
            
            self.display()
            self.state = GUIBraketest.WAIT
            self.distance = 0
    
    def set_canvas(self, frame):
        self.frame = tkinter.Frame(frame, border=0, bg=constants.background_color, relief="groove",
                                            highlightthickness=True, highlightcolor=constants.text_color)
        tkinter.Label(self.frame, text="Speed (km/h)", bg=constants.background_color, fg=constants.text_color,
                      font=('Helvetica 15 bold')).grid(row=0, sticky='W', rowspan=2)
        tkinter.Label(self.frame, textvariable=self.speed_var, bg=constants.background_color, fg=constants.text_color, justify=tkinter.LEFT, anchor="w", width=12, 
                      font=('Helvetica 20 bold')).grid(row=2, sticky='W', columnspan=2)
        
        tkinter.Label(self.frame, text="Brake distance (m)", bg=constants.background_color, fg=constants.text_color,
                      font=('Helvetica 15 bold')).grid(row=3, sticky='W', columnspan=2)
        tkinter.Label(self.frame, textvariable=self.distance_var, bg=constants.background_color, fg=constants.text_color, justify=tkinter.LEFT, anchor="w", width=12,  
                      font=('Helvetica 20 bold')).grid(row=4, sticky='W', columnspan=2)
        
        tkinter.Checkbutton(self.frame, text='Write', variable=self.write_var, bg=constants.background_color, fg=constants.text_color).grid(row=0, column=1, sticky='W')
        tkinter.Checkbutton(self.frame, text='Log', variable=self.log_var, bg=constants.background_color, fg=constants.text_color).grid(row=1, column=1, sticky='W')
    
    def reset(self):
        self.initial_speed = 0
        self.final_speed = 0
        self.distance = 0
        self.brake_time = 0
        
        self.x = 0
        self.y = 0
        self.z = 0
        
        self.brakedata.clear()
        
        self.display()
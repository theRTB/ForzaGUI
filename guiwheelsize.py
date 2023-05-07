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

'''
TODO:
 - if wheelsize is known, derive slip ratio for driven wheels
 - consider forcing pitch to be near 0 (car is on flat ground) for prerequisite
'''    

TIRES = ['FL', 'FR', 'RL', 'RR']

# modified from wikipedia: 
# https://en.wikipedia.org/wiki/Algorithms_for_calculating_variance
class WelfordsOnline():
    def __init__(self):
        self.count = 0
        self.mean = 0
        self.M2 = 0
    
    # For a new value newValue, compute the new count, new mean, the new M2.
    # mean accumulates the mean of the entire dataset
    # M2 aggregates the squared distance from the mean
    # count aggregates the number of samples seen so far
    def update(self, newValue):
        self.count += 1
        delta = newValue - self.mean
        self.mean += delta / self.count
        delta2 = newValue - self.mean
        self.M2 += delta * delta2
    
    def get_count(self):
        return self.count
    
    def get_mean(self):
        return self.mean
    
    def get_variance(self):
        if self.count < 1:
            return float('nan')
        return self.M2 / self.count
    
    def get_sample_variance(self):
        if self.count < 2:
            return float('nan')
        return self.M2 / (self.count - 1)
    
    def reset(self):
        self.__init__()

class GUIWheelsize:
    COLLECTING_MINSPEED =  8 / 3.6 #  8 kmh
    COLLECTING_MAXSPEED = 20 / 3.6 # 20 kmh
    
    #TODO: make this an enum?
    STATE_OTHER = 0 #do nothing
    STATE_COLLECTING = 1 #collect if prerequisites are met
    STATE_COLLECTED = 2 #update slip ratio because wheel size is now known
    
    UPPER_BOUND_VARIANCE = 5e-05
    UPPER_BOUND_COUNT = 480 #240/2 = 240 frames = 4 seconds
    LOWER_BOUND_COUNT = 240 #240/2 = 120 frames = 2 seconds
    
    # WHEELSIZE_MIN =   5 #cm
    # WHEELSIZE_MAX = 250 #cm
    
    def __init__(self, logger, *args, **kwargs):
        self.logger = logger
        
        self.front_var = tkinter.DoubleVar(value=0.00)
        self.rear_var = tkinter.DoubleVar(value=0.00)
        
        self.state = self.STATE_OTHER
        self.wheelsize_front = 0
        self.wheelsize_rear  = 0
        
        self.front = WelfordsOnline()
        self.rear = WelfordsOnline()
        
        self.tracking_var = tkinter.IntVar(value=1)        

    def display(self):
        if self.state == self.STATE_COLLECTING:
            self.front_var.set(f'{self.front.get_mean():.2f}')
            self.rear_var.set(f'{self.rear.get_mean():.2f}')

    #TODO: add requirement of no pitch -> car is on flat ground
    def in_collecting_state(self, fdp):
        in_speed_bounds = (fdp.speed >= self.COLLECTING_MINSPEED and 
                          fdp.speed <= self.COLLECTING_MAXSPEED)
        inputs_zero = all(v==0 for v in fdp.to_list(['steer', 'accel', 
                                                     'brake', 'handbrake']))
        return (fdp.is_race_on != 0 and in_speed_bounds and inputs_zero)
    
    def is_variance_stable(self):
        return (self.front.get_sample_variance() <= self.UPPER_BOUND_VARIANCE and 
                self.rear.get_sample_variance()  <= self.UPPER_BOUND_VARIANCE and
                self.front.get_count() > self.COUNT_LOWER_BOUND and 
                self.rear.get_count() > self.COUNT_LOWER_BOUND)
    
    def update(self, fdp):
        if self.state == self.STATE_OTHER:
            return
        if self.state == self.STATE_COLLECTING:
            if not self.in_collecting_state(fdp):
                return
            self.add_datapoint(fdp)
            if self.is_variance_stable():
                self.wheelsize_front = self.front.get_mean()
                self.wheelsize_rear = self.rear.get_mean()
                self.set_tracking(False)
                self.logger.info(f"Wheelsize determined {self.front.get_mean():.2f} {self.rear.get_mean():.2f} cm")
            elif (self.front.get_count() > self.UPPER_BOUND_COUNT and 
                  self.rear.get_count() > self.UPPER_BOUND_COUNT):
                self.logger.info(f'Wheelsize reset: {self.front.get_sample_variance():.2e} {self.rear.get_sample_variance():.2e} variance not under {self.UPPER_BOUND_VARIANCE:.2e}, keep rolling')
                self.front.reset()
                self.rear.reset()
        if self.state == self.STATE_COLLECTED:
            pass
            #TODO: add slip ratio measurements
        
    def add_datapoint(self, fdp):
        for wheel, side in zip(TIRES, [self.front]*2 + [self.rear]*2):
            rotation_speed = abs(getattr(fdp, f"wheel_rotation_speed_{wheel}"))
            if rotation_speed == 0:
                continue
            radius = 100 * fdp.speed  / rotation_speed #convert to cm
            # if (radius < GUIWheelsize.WHEELSIZE_MIN or 
            #     radius > GUIWheelsize.WHEELSIZE_MAX):
            #     continue
            side.update(radius)
            
    #return dict, intended for traces
    def get_wheelsizes(self):
        return {'wheelsize_front': self.wheelsize_front,
                'wheelsize_rear':  self.wheelsize_rear}
    
    #carinfo is a dict, intended for traces
    def set_wheelsizes(self, carinfo):
        if 'wheelsize_front' in carinfo and 'wheelsize_rear' in carinfo:
            self.wheelsize_front = float(carinfo['wheelsize_front'])
            self.wheelsize_rear  = float(carinfo['wheelsize_rear'])
            self.front_var.set(f'{self.wheelsize_front:.2f}')
            self.rear_var.set(f'{self.wheelsize_rear:.2f}')
            self.set_tracking(False)
            
    def set_tracking(self, enable):
        if enable:
            self.tracking_var.set(1)
        else:
            self.tracking_var.set(0)
        # self.tracking_button.invoke() #seems to have a race condition where self.tracking_var is not yet updated to 0?
        self.tracking_handler()

    def tracking_handler(self):
        if self.tracking_var.get():
            self.reset()
            self.state = self.STATE_COLLECTING
        elif self.wheelsize_front == 0 or self.wheelsize_rear == 0:
            self.state = self.STATE_OTHER
        else: #wheelsizes have been set
            self.state = self.STATE_COLLECTED
    
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
        tkinter.Label(self.frame, textvariable=self.front_var, width=5, 
                      **opts).grid(row=row, column=1, sticky=tkinter.E)
        tkinter.Label(self.frame, textvariable=self.rear_var, width=5, 
                      **opts).grid(row=row, column=2, sticky=tkinter.E)
        
        row += 1 
        self.tracking_button = tkinter.Checkbutton(self.frame, 
                                    text='Tracking', variable=self.tracking_var, 
                                    command=self.tracking_handler, bg=constants.background_color, 
                                    fg=constants.text_color)
        self.tracking_button.grid(row=row, column=1, columnspan=2)
        
    def reset(self):
        self.state = self.STATE_OTHER
        self.front.reset()
        self.rear.reset()
        self.front_var.set(0.00)
        self.rear_var.set(0.00)
# -*- coding: utf-8 -*-
"""
Created on Sun Feb 13 15:16:10 2022

@author: RTB
"""

import tkinter
import tkinter.ttk

import constants
import math

#min(x,5) to make sure scalar is f(5) for all n > 5
tanh_offset = lambda x: math.tanh(0.31 * min(x, 5) + 0.76)
#tanh_offset = lambda x: 1 -math.tanh(0.31 * min(x, 5) + 0.76)

#scale to gear that contains top speed by ratio
#scale to percentage of top speed in all the gears, thrown into tanh

ILLUMINATION_INTERVAL = int(1.6*60)

class GUILedDummy:
    def __init__(self, logger):
        pass
        
    def set_rpmtable(self, rpmtable, rpmvalues, gears, revlimit, collectedingear):
        pass
        
    def update (self, fdp):
        pass

    def update_leds(self):
        pass
    
    def set_canvas(self, frame):
        pass
    
    def reset(self):
        pass

class GUILed:
    def __init__(self, logger):
        self.logger = logger
        
        self.ledbar = [None for x in range(15)]
        self.ledstatus = [False for x in range(15)]
        self.topled = None
        self.bottomled = None
        self.ledcolor = 'red'
        
        self.led_canvas = None
        
        self.lower_bound = [5000 for x in range(11)]
        self.shiftrpm = [7000 for x in range(11)]
        
        self.step = [(self.shiftrpm[x] - self.lower_bound[x])/12 for x in range(11)]
        
        self.state = 0
        
    def set_rpmtable(self, rpmtable, rpmvalues, gears, revlimit, collectedingear):
        print(f"revlimit {revlimit} collectedingear {collectedingear}")
        for gear, rpm in enumerate(rpmtable):
            if rpm == 0: #rpmtable has initial 0 and 0 for untested gears
                continue
            #print(f"rpm {rpm} gear {gear}")
            if abs(rpm - revlimit) < int(0.001*revlimit):
                rpm = int(tanh_offset(gear)*rpm)
                #print(f"adjusting rpm to {rpm} due to revlimit proximity")
            
            scalar = gears[gear-1] / gears[collectedingear-1]
            #print(f"scalar is {scalar}")
            for j, x in enumerate(rpmvalues):
                if x >= rpm:
                    offset = int(max(j - scalar*ILLUMINATION_INTERVAL, 0))
                    self.lower_bound[gear] = int(rpmvalues[offset])
                    #print(f"j {j} val {rpmvalues[j]} offset {offset}")
                    break
                
            self.shiftrpm[gear] = rpm
            self.step[gear] = (self.shiftrpm[gear] - self.lower_bound[gear])/12
            #self.logger.info(f"adjusted shift rpm {self.shiftrpm[gear]} "
             #                f"lower bound {self.lower_bound[gear]}")
        
    def update (self, fdp):
        state = int((fdp.current_engine_rpm - self.lower_bound[fdp.gear]) / self.step[fdp.gear])
        if state < 0:
            state = 0
        if state > 12:
            state += 1
        if state > 15:
            state = 15
        
        for i in range(state):
            self.ledstatus[i] = True
        for i in range(state, 15):
            self.ledstatus[i] = False
            
        if state == 12:
            self.ledcolor = 'cyan'
            self.ledstatus[12] = True
        else:
            self.ledcolor = 'red'
            
        self.update_leds()
        self.state = state

    def update_leds(self):
        for i in range(15):
            if self.ledstatus[i]:
                self.led_canvas.itemconfig(self.ledbar[i], fill=self.ledcolor)
            else:
                self.led_canvas.itemconfig(self.ledbar[i], fill='black')
        self.led_canvas.itemconfig(self.topled, fill=self.ledcolor)
        self.led_canvas.itemconfig(self.bottomled, fill=self.ledcolor)
    
    def set_canvas(self, frame):
        self.led_canvas = tkinter.Canvas(frame, border=0, bg=constants.background_color, relief="groove",
                                            highlightthickness=True, highlightcolor=constants.text_color)
        self.led_canvas.place(relx=0.0, rely=0.55,
                                width=500, height=90,
                                anchor=tkinter.W)
        tkinter.Label(self.led_canvas, text="LED gearshifts", bg=constants.background_color, fg=constants.text_color,
                      font=('Helvetica 15 bold')).place(relx=0.5, rely=0.2, anchor=tkinter.CENTER)
        
        for i in range(15):
            self.ledbar[i] = self.led_canvas.create_rectangle(10+30* i, 40,10+30+30* i,40+30, fill='black', outline='white')
        self.topled =        self.led_canvas.create_rectangle(10+30*11, 30,10+30+30*12, 30+10, fill='red',   outline='white')
        self.bottomled =     self.led_canvas.create_rectangle(10+30*11, 70,10+30+30*12,70+10, fill='red',   outline='white')
        
       # self.led_canvas.create_line(0,0, 500-1,0, 500-1,200-1, 0,200-1, 0,0, fill='white')
    
    def reset(self):
        for i in range(15):
            self.ledstatus[i] = False
            self.led_canvas.itemconfig(self.ledbar[i], fill='black')
            
        self.led_canvas.itemconfig(self.topled, fill='red')
        self.led_canvas.itemconfig(self.bottomled, fill='red')
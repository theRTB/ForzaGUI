# -*- coding: utf-8 -*-
"""
Created on Sun Jun 12 09:44:19 2022

@author: RTB
"""

import tkinter
import tkinter.ttk

from collections import deque
import statistics

import constants
import math
import csv
#self.gearratios = [{'median':0, 'deque':deque(maxlen=240)} for x in range(1,12)]
#'acceleration_x', 'acceleration_y', 'acceleration_z',
#        'tire_slip_ratio_FL', 'tire_slip_ratio_FR',
#        'tire_slip_ratio_RL', 'tire_slip_ratio_RR',

'''
TireSlipRatioFrontLeft << this is longitudal slip or just spin.
TireSlipAngleFrontLeft << this is lateral tire slip angle (not the same as wheel angle).
TireCombinedSlipFrontLeft; << this is combination of the two above. Although the way they normalize this, it is hard to make sense of this third value.

None of those three show weight distribution, not sure what you mean by “angle of road force on tire”, and none of those show fraction of max possible grip. 
Also, just to be completely clear. None of them show tire load.

TireSlipRatioFrontLeft can be used to calculate Fx, and TireSlipAngleFrontLeft could be used to calculate Fy at pure slip. 
TireCombinedSlipFrontLeft can be used to calculate the same at combined slip.

Side force (Fy) and friction force (Fx) 


'''

'''
TODO:
    track lateral G over speed given tire grip < 1.5.
    

'''

MAXLEN = 300
G = 9.81
RED = '#ee2222'
ORANGE = '#eeaa00'
TIRES = ['FL', 'FR', 'RL', 'RR']

MAXG = 8
SLIPLIMIT = 1.5

class GUILateralGDummy:
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
    
#implements a short deque that rolls over into a long deque
#maintains a rolling sum for a rolling average
#starts filled with zeros, so averages are not correct until filled
class double_deque():
    def __init__(self, shortlen, totallen):
        self.shortlen = shortlen
        self.totallen = totallen
        self.longlen = totallen - shortlen
        
        self.short = deque(maxlen=self.shortlen)
        self.long = deque(maxlen=self.longlen)
        
        self.reset()
    
    #assumes short and long are filled to maxlen
    def append(self, val):
        popval = self.short.popleft()
        self.short_rollingsum = self.short_rollingsum - popval + val
        self.long_rollingsum = self.long_rollingsum - self.long[0] + popval
        self.long.append(popval)
        self.short.append(val)

    def reset(self):
        self.short.extend([0]*self.shortlen)
        self.long.extend([0]*self.longlen)
        
        self.short_rollingsum = 0
        self.long_rollingsum = 0     
    
    def short_avg(self):
        return self.short_rollingsum / self.shortlen
    
    def long_avg(self):
        return self.long_rollingsum / self.longlen

class GUILateralG:
    # rownames = ['speed', 
    #            'velocity_x' , 'velocity_y', 'velocity_z',
    #            'acceleration_x', 'acceleration_y', 'acceleration_z',
    #            'angular_velocity_x', 'angular_velocity_y', 'angular_velocity_z', 
    #            'tire_slip_ratio_FL', 'tire_slip_ratio_FR', 'tire_slip_ratio_RL', 'tire_slip_ratio_RR',
    #            'tire_slip_angle_FL', 'tire_slip_angle_FR', 'tire_slip_angle_RL', 'tire_slip_angle_RR',
    #            'position_x', 'position_y', 'position_z',
    #            'tire_temp_FL', 'tire_temp_FR', 'tire_temp_RL', 'tire_temp_RR' ]
    MAX_DATAPOINTS = 60
    SHORTLEN = 10
    TOTALLEN = 300
    def __init__(self, logger):
        self.logger = logger
          
        self.accelx_deque = double_deque(shortlen=GUILateralG.SHORTLEN, 
                                         totallen=GUILateralG.TOTALLEN)
        self.accely_deque = double_deque(shortlen=GUILateralG.SHORTLEN, 
                                         totallen=GUILateralG.TOTALLEN)
        self.accelz_deque = double_deque(shortlen=GUILateralG.SHORTLEN, 
                                         totallen=GUILateralG.TOTALLEN)
        
        self.accelx_shortavg_var = tkinter.StringVar()
        self.accely_shortavg_var = tkinter.StringVar()
        self.accelz_shortavg_var = tkinter.StringVar()
        self.accel_shortavg_var = tkinter.StringVar()
        
        self.accelx_longavg_var = tkinter.StringVar()
        self.accely_longavg_var = tkinter.StringVar()
        self.accelz_longavg_var = tkinter.StringVar()        
        self.accel_longavg_var = tkinter.StringVar()
        
        self.accelx_label= tkinter.Label()
        
        self.arrow = {t:{d:tkinter.Label() for d in ['U', 'L', 'R', 'D']} for t in TIRES}
        
        self.latgdata = []
        
        self.reset()
    
    def tiregripcolor (self, tireneg, tirepos, slipvalue):
        newcolor = constants.text_color
        if slipvalue > 2:
            newcolor = RED
        elif slipvalue > 1:
            newcolor = ORANGE
        tirepos.configure(fg=newcolor)
        
        newcolor = constants.text_color
        if -slipvalue > 2:
            newcolor = RED
        elif -slipvalue > 1:
            newcolor = ORANGE
        tireneg.configure(fg=newcolor)
    
    def display(self):
        accelx_shortavg = self.accelx_deque.short_avg()
        accely_shortavg = self.accely_deque.short_avg()
        accelz_shortavg = self.accelz_deque.short_avg()
        accelx_longavg = self.accelx_deque.long_avg()
        accely_longavg = self.accely_deque.long_avg()
        accelz_longavg = self.accelz_deque.long_avg()
        accel_shortavg = math.sqrt(accelx_shortavg**2 + accely_shortavg**2 + accelz_shortavg**2)
        accel_longavg = math.sqrt(accelx_longavg**2 + accely_longavg**2 + accelz_longavg**2)
        
        # if (abs(self.tire_slip_ratio_FL) > 1 or abs(self.tire_slip_ratio_FR) > 1 or
        #     abs(self.tire_slip_ratio_RL) > 1 or abs(self.tire_slip_ratio_RR) > 1):
        #     self.accelx_label.configure(fg="#dd2222")
        # else:
        #     self.accelx_label.configure(fg=constants.text_color)
        
        for tire in ['FL', 'FR', 'RL', 'RR']:
            self.tiregripcolor(self.arrow[tire]['U'], self.arrow[tire]['D'], self.tire_slip_ratio[tire])
            self.tiregripcolor(self.arrow[tire]['L'], self.arrow[tire]['R'], self.tire_slip_angle[tire])
        
        self.accelx_shortavg_var.set(f"{accelx_shortavg: .2f}")
        self.accely_shortavg_var.set(f"{accely_shortavg: .2f}")
        self.accelz_shortavg_var.set(f"{accelz_shortavg: .2f}")
        self.accel_shortavg_var.set(f"{accel_shortavg: .2f}")
        
        self.accelx_longavg_var.set(f"{accelx_longavg: .2f}")
        self.accely_longavg_var.set(f"{accely_longavg: .2f}")
        self.accelz_longavg_var.set(f"{accelz_longavg: .2f}")
        self.accel_longavg_var.set(f"{accel_longavg: .2f}")
                

    def update(self, fdp):
        if fdp.is_race_on == 0:
            return
        
        self.accelx_deque.append(fdp.acceleration_x/G)
        self.accely_deque.append(fdp.acceleration_y/G)
        self.accelz_deque.append(fdp.acceleration_z/G)
        
        self.tire_slip_ratio['FL'] = fdp.tire_slip_ratio_FL
        self.tire_slip_ratio['FR'] = fdp.tire_slip_ratio_FR
        self.tire_slip_ratio['RL'] = fdp.tire_slip_ratio_RL
        self.tire_slip_ratio['RR'] = fdp.tire_slip_ratio_RR
        
        self.tire_slip_angle['FL'] = fdp.tire_slip_angle_FL
        self.tire_slip_angle['FR'] = fdp.tire_slip_angle_FR
        self.tire_slip_angle['RL'] = fdp.tire_slip_angle_RL
        self.tire_slip_angle['RR'] = fdp.tire_slip_angle_RR
        
        self.latgdata.append([fdp.acceleration_x/G, fdp.acceleration_z/G, fdp.speed] + [self.tire_slip_angle[x] for x in TIRES])
        
        # if len(self.latgdata) == GUILateralG.MAX_DATAPOINTS:
        #     with open('latgdata.csv', 'w', newline='') as rawcsv:
        #         csvobject = csv.writer(rawcsv, delimiter='\t', quotechar='', quoting=csv.QUOTE_NONE)    
        #         csvobject.writerow(GUILateralG.rownames)
        #         csvobject.writerows(self.latgdata) 
        #     self.latgdata.clear()
        #     self.logger.info("Written data to latgdata.csv")
        # else:
        #     point = fdp.to_list(GUILateralG.rownames)
        #     self.latgdata.append(point)

    def to_file(self, seconds=0):
        with open('lateralgdata.csv', 'w', newline='') as rawcsv:
            csvobject = csv.writer(rawcsv, delimiter='\t', quotechar='', quoting=csv.QUOTE_NONE)    
            csvobject.writerow(['latg', 'longg', 'speed', 'slipFL', 'slipFR', 'slipRL', 'slipRR'])
            csvobject.writerows(self.latgdata[-seconds*60:])   
        self.logger.info(f"Written {len(self.latgdata[-seconds*60:])} rows to file")

    def set_canvas(self, frame):
        self.frame = tkinter.Frame(frame, border=0, bg=constants.background_color, relief="groove",
                                            highlightthickness=True, highlightcolor=constants.text_color)
        opts = {'bg':constants.background_color, 'fg':constants.text_color, 'justify':tkinter.RIGHT, 'anchor':tkinter.E,
                      'font':('Helvetica 10 bold')}
        
        tkinter.Label(self.frame, text='axis', **opts).grid(row=0)
        tkinter.Label(self.frame, text=' 0.17s', **opts).grid(row=0, column=1)
        tkinter.Label(self.frame, text=' 5s', **opts).grid(row=0, column=2)
        
        opts['font'] = ('Helvetica 16 bold')
        
        tkinter.Label(self.frame, text='X:', **opts).grid(row=1)        
        tkinter.Label(self.frame, text='Y:', **opts).grid(row=2)
        tkinter.Label(self.frame, text='Z:', **opts).grid(row=3)
        tkinter.Label(self.frame, text='g:', **opts).grid(row=4)
        
        opts['width'] = 4
        
        tkinter.Label(self.frame, textvariable=self.accelx_shortavg_var, **opts).grid(row=1, column=1)        
        tkinter.Label(self.frame, textvariable=self.accely_shortavg_var, **opts).grid(row=2, column=1)
        tkinter.Label(self.frame, textvariable=self.accelz_shortavg_var, **opts).grid(row=3, column=1)
        tkinter.Label(self.frame, textvariable=self.accel_shortavg_var,  **opts).grid(row=4, column=1)
        
        tkinter.Label(self.frame, textvariable=self.accelx_longavg_var, **opts).grid(row=1, column=2)        
        tkinter.Label(self.frame, textvariable=self.accely_longavg_var, **opts).grid(row=2, column=2)
        tkinter.Label(self.frame, textvariable=self.accelz_longavg_var, **opts).grid(row=3, column=2)
        tkinter.Label(self.frame, textvariable=self.accel_longavg_var,  **opts).grid(row=4, column=2)
        
        button = tkinter.Button(self.frame, text='Dump', bg=constants.background_color, fg=constants.text_color,
                                borderwidth=3, highlightcolor=constants.text_color, highlightthickness=True)
        button.bind('<Button-1>', lambda x: self.to_file())
        button.grid(row=0, column=3)
        
        button5 = tkinter.Button(self.frame, text='5s', bg=constants.background_color, fg=constants.text_color,
                                borderwidth=3, highlightcolor=constants.text_color, highlightthickness=True)
        button5.bind('<Button-1>', lambda x: self.to_file(seconds=5))
        button5.grid(row=1, column=3)
                        
        #🢀 🢂 🢁 🢃
        self.arrowframe = tkinter.Frame(frame, border=0, bg=constants.background_color, relief="groove",
                                            highlightthickness=True, highlightcolor=constants.text_color)
        rowoffset = 0
        coloffset = 0
        opts = {'bg':constants.background_color, 'fg':constants.text_color, 'font':('Helvetica 16 bold')}
        for tire in ['FL', 'FR', 'RL', 'RR']:
            rowoffset = 0 if tire[0] == 'F' else 3
            coloffset = 0 if tire[1] == 'L' else 2
                
            self.arrow[tire]['U'] = tkinter.Label(self.arrowframe, text="🢁", **opts)
            self.arrow[tire]['L'] = tkinter.Label(self.arrowframe, text="🢀", **opts)
            self.arrow[tire]['R'] = tkinter.Label(self.arrowframe, text="🢂", **opts)
            self.arrow[tire]['D'] = tkinter.Label(self.arrowframe, text="🢃", **opts)
            
            self.arrow[tire]['U'].grid(row=0+rowoffset, column=0+coloffset, padx=0, pady=0, columnspan=2)
            self.arrow[tire]['L'].grid(row=1+rowoffset, column=0+coloffset, padx=0, pady=0)
            self.arrow[tire]['R'].grid(row=1+rowoffset, column=1+coloffset, padx=0, pady=0)
            self.arrow[tire]['D'].grid(row=2+rowoffset, column=0+coloffset, padx=0, pady=0, columnspan=2)
    
    def reset(self):
        self.accelx_deque.reset()
        self.accely_deque.reset()
        self.accelz_deque.reset()  
        
        self.tire_slip_ratio = {t:0 for t in TIRES}
        self.tire_slip_angle = {t:0 for t in TIRES}
        
        self.latgdata.clear()
        
        self.display()
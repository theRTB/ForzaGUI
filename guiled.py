# -*- coding: utf-8 -*-
"""
Created on Sun Feb 13 15:16:10 2022

@author: RTB
"""

import tkinter
import tkinter.ttk
import constants
import math
import numpy as np

#for the audio cue for shifting
import winsound

#for importing config
import json
from os.path import exists

from collections import deque
from itertools import groupby, dropwhile

from dragderivation import Trace, DragDerivation

'''
TODO:    
    derive expected time in gear shifting optimally
    
    add displayed difference of reaction time state vs actual shift
    
    add linear extrapolation when looking up how far to run backwards on the rpm/speed array
    this in case the result goes below the minimum rpm collected
    
    set a minimum distance in rpm between states for high gears
    
    grey out and untick Gear tickbox if Lights tickbox is off
    
    blank shift leds after detecting gear change
    gear change is a gradual process in telemetry: power is cut (negative), then gear changes, then power goes positive again
    blank on gear variable changing is simplest, but can be very slow
    we can use inputs: https://pypi.org/project/inputs/0.3/
    or https://gist.github.com/artizirk/b407ba86feb7f0227654f8f5f1541413
    or https://github.com/bayangan1991/PYXInput
'''

FILENAME_SETTINGS = 'settings_guiled.json'
DEFAULTCONFIG = {"shiftlight_x": 960, "shiftlight_y": 540, #middle of a 1080p screen, safe enough
                 "illumination_interval": 60, #must be divisible by 4 and 5
                 "reaction_time": 6,  #frames within shift state until optimal shift rpm
                 "reaction_time_tone": 6, #frames within shift state until optimal shift rpm (audio cue)
                 "distance_from_revlimit_ms": 5, #in frames
                 "distance_from_revlimit_pct": .99,   #99.0% of rev limit
                 "hysteresis_pct_revlimit": .05,  #drop state only after rpm drops x% of rev limit
                 # "state_dropdown_delay": 0, #dropping state only allowed after x frames
                 "led_height": 40, #in pixels
                 "led_width": 40,  #in pixels
                 "sequence": 'linear', #linear or sides
                 "audiofile": "audiocheck.net_sin_1000Hz_-3dBFS_0.1s.wav"}

config = DEFAULTCONFIG
if exists(FILENAME_SETTINGS):
    with open(FILENAME_SETTINGS) as file:
        config.update(json.load(file))
with open(FILENAME_SETTINGS, 'w') as file:
    json.dump(config, file, indent=4)

class Shiftlight():
    BLACK = '#000000'
    GREEN = '#80FF80'
    AMBER = '#FFBF7F'
    RED   = '#FF8088'
    BLUE  = '#8080FF'
    CYAN  = '#80FFFF'
    
    START_X = 0
    START_Y = 0
    
    PATTERN_SIDES = [
        [BLACK]*10,
        [GREEN] + [BLACK]*8 + [GREEN],
        [GREEN, AMBER] + [BLACK]*6 + [AMBER, GREEN],
        [GREEN, AMBER, AMBER] + [BLACK]*4 + [AMBER, AMBER, GREEN],
        [GREEN, AMBER, AMBER, RED] + [BLACK]*2 + [RED, AMBER, AMBER, GREEN],
        [CYAN]*10,                                                         #shift state, or reaction time state
        [RED, CYAN, RED, CYAN, RED, RED, CYAN, RED, CYAN, RED],            #overrev state
        [RED]*10 ]                                                         #rev limit state
    
    LED_COUNT = 10
    LED_OFFSETS_SIDES = [70, 40,   20, 10, 0, 0, 10, 20,   40, 70] #scaled to 70 led_height
    
    #mclaren pattern with added rev limit state
    PATTERN_LINEAR = [
        [BLACK]*10,
        [GREEN, GREEN] + [BLACK]*8,
        [GREEN, GREEN, AMBER, AMBER] + [BLACK]*6,
        [GREEN, GREEN, AMBER, AMBER, AMBER, AMBER, ] + [BLACK]*4,
        [GREEN, GREEN, AMBER, AMBER, AMBER, AMBER, RED, RED] + [BLACK]*2,
        [CYAN]*10,                                                         #shift state, or reaction time state
        [RED, CYAN, RED, CYAN, RED, RED, CYAN, RED, CYAN, RED],            #overrev state
        [RED]*10 ]                                                         #rev limit state
    
    LED_OFFSETS_LINEAR = [0]*LED_COUNT
    
    @classmethod
    def variables(cls, sequence='linear'):
        if sequence == 'linear':
            return (Shiftlight.PATTERN_LINEAR, Shiftlight.LED_OFFSETS_LINEAR, Shiftlight.LED_COUNT)
        else: #sides
            return (Shiftlight.PATTERN_SIDES, Shiftlight.LED_OFFSETS_SIDES, Shiftlight.LED_COUNT)
    
START_X = 0
START_Y = 0
LED_HEIGHT = config['led_height']
LED_WIDTH = config['led_width']
STATES, LED_OFFSETS_Y, LED_COUNT = Shiftlight.variables(sequence=config['sequence'])

LED_OFFSETS_Y = [int(y/70*LED_HEIGHT) for y in LED_OFFSETS_Y]

STATE_REVLIMIT = len(STATES)-1
STATE_OVERREV = STATE_REVLIMIT-1
STATE_SHIFT = STATE_OVERREV-1
    
HEIGHT = LED_HEIGHT+max(LED_OFFSETS_Y)+1
WIDTH = LED_WIDTH*LED_COUNT+1

GEAR_HEIGHT = 110 #height of the gear display

#extend tkinter.Variable? get and set functions are only set for the subtypes
#consider property() functionality
class Variable():
    def __init__(self, name, defaultvalue, vartype, unit):
        self.name = name
        self.defaultvalue = defaultvalue
        self.vartype = vartype
        self.unit = unit
        
    def get(self):
        return self.var.get()
    
    def set(self, value):
        return self.var.set(value)

    def init_tkintervar(self):
        if self.vartype == 'String':
            self.var = tkinter.StringVar(value=self.defaultvalue)
        elif self.vartype == 'Double':
            self.var = tkinter.DoubleVar(value=self.defaultvalue)
        elif self.vartype == 'Int':
            self.var = tkinter.IntVar(value=self.defaultvalue)
        
#convenient class for displaying and modifying variables live in the GUI
class V(): 
    illumination_interval = Variable('Illumination interval', config['illumination_interval'], 'Int', 'frames')  #1.0 seconds
    reaction_time = Variable('LED offset', config['reaction_time'], 'Int', 'frames')
    reaction_time_tone = Variable('Tone offset', config['reaction_time_tone'], 'Int', 'frames')
    distance_from_revlimit_ms = Variable('Distance from revlimit', config['distance_from_revlimit_ms'], 'Int', 'frames')
    distance_from_revlimit_pct = Variable('Distance from revlimit', config['distance_from_revlimit_pct'], 'Double', 'pct revlimit')
    hysteresis_pct_revlimit = Variable('Hysteresis downwards', config['hysteresis_pct_revlimit'], 'Double', 'pct revlimit')
    # state_dropdown_delay = Variable('State dropdown delay', config['state_dropdown_delay'], 'Int', 'frames')  
    shiftlight_x = Variable('Shiftlight location x', config['shiftlight_x'], 'Int', 'pixels')
    shiftlight_y = Variable('Shiftlight location y', config['shiftlight_y'], 'Int', 'pixels')
    
    #initializing tkinter variable must be done after creating a tkinter root window
    @classmethod 
    def _init_tkintervariables(cls):
        for name, value in cls.__dict__.items():
            if name[0] == '_':
                continue
            value.init_tkintervar()
    
    @classmethod
    def _var_list(cls):
        return [var for name, var in cls.__dict__.items() if name[0] != '_']
    
    @classmethod
    def _to_config(cls):
        return {name:var.get() for name, var in cls.__dict__.items() if name[0] != '_'}

class GUILed:
    def __init__(self, logger, root, *args, **kwargs):
        self.logger = logger
        
        self.ledbar = [None for x in range(10)]
        
        self.frame = None
        
        self.run_shiftleds = [False for x in range(11)]
        self.state_table = [[tkinter.IntVar() for x in range(0, len(STATES))] for y in range(11)]
        self.downshift_limit = [0]*11
        
        self.audio_cue_rpm = [0 for x in range(11)]
        self.beep_counter = 0
        
        self.state = 0
        self.statedowntimer = 0
        
        self.update_rpm_var = True
        self.rpm_var = tkinter.IntVar(value=0)
        self.gear_var = tkinter.StringVar(value='1')
        
        self.display_lights_var = tkinter.BooleanVar(value=True)
        self.display_gearnr_var = tkinter.BooleanVar(value=True)
        self.play_beep_var = tkinter.BooleanVar(value=True)
        
        self.deque = deque(maxlen=150)
        self.log_shifts_var = tkinter.BooleanVar(value=False)
    
        self.__init__window(root)
        V._init_tkintervariables()
    
    #create window with true red canvas and transparentcolor true red
    def __init__window(self, root):
        self.window = tkinter.Toplevel(root)
        self.window.wm_attributes("-topmost", 1) #force always on top
        self.window.wm_attributes('-transparentcolor', 'red')
        self.window.overrideredirect(True) #remove title bar, needs code to allow window to move
        self.window.geometry(f"{WIDTH}x{HEIGHT+GEAR_HEIGHT}+{V.shiftlight_x.defaultvalue}+{V.shiftlight_y.defaultvalue}")
        self.window.configure(bg='red')
        
        self.canvas = tkinter.Canvas(self.window, width=WIDTH, height=HEIGHT, bg='red', highlightthickness=0)
        self.canvas.pack(expand=False, fill='both')
        
        self.gear_label = tkinter.Label(self.window, textvariable=self.gear_var, font=('Helvetica 100 bold'), fg='#FFFFFF', bg='black')
        self.gear_label.pack(expand=True, fill='y')
           
        for i in range(LED_COUNT):
            self.ledbar[i] = self.canvas.create_rectangle(START_X+LED_WIDTH*i, START_Y+LED_OFFSETS_Y[i],
                                                     START_X+LED_WIDTH*(i+1),START_Y+LED_HEIGHT+LED_OFFSETS_Y[i], 
                                                     fill='black', outline='white')
            
            #vertical bar, remember to swap *LED_COUNT from WIDTH to HEIGHT 
            # self.ledbar[i] = self.canvas.create_rectangle(START_X,           START_Y+LED_HEIGHT*i, 
            #                                              START_X+LED_WIDTH, START_Y+LED_HEIGHT*(i+1), 
            #                                              fill='black', outline='white')
        
        #from https://stackoverflow.com/questions/4055267/tkinter-mouse-drag-a-window-without-borders-eg-overridedirect1
        self.window.bind("<ButtonPress-1>", self.start_move)
        self.window.bind("<ButtonRelease-1>", self.stop_move)
        self.window.bind("<B1-Motion>", self.do_move)

    def start_move(self, event):
        self.x = event.x
        self.y = event.y

    def stop_move(self, event):
        deltax = event.x - self.x
        deltay = event.y - self.y
        V.shiftlight_x.set(self.window.winfo_x() + deltax)
        V.shiftlight_y.set(self.window.winfo_y() + deltay)
        self.logger.info(f"ledbar offset {V.shiftlight_x.get()} and {V.shiftlight_y.get()}")
        self.x = None
        self.y = None

    def do_move(self, event):
        deltax = event.x - self.x
        deltay = event.y - self.y
        x = self.window.winfo_x() + deltax
        y = self.window.winfo_y() + deltay
        self.window.geometry(f"+{x}+{y}")

    #TODO: remove revlimit from function, derive from trace
    def set_rpmtable(self, rpmtable, revlimit, trace):
        self.logger.info(f"revlimit {int(revlimit)} gear_collected {trace.gear_collected}")
        
        self.rpmtable = rpmtable
        self.revlimit = revlimit
        
        self.drag = DragDerivation(trace.gears, final_drive=1, trace=trace)
        self.geardata = DragDerivation.derive_timespeed_all_gears(**self.drag.__dict__)
        
        lim = int(len(trace.rpm)/10) #find close fitting ratio for rpm/speed based on the last 10% of the sweep
        rpmspeedratio = np.average(trace.rpm[-lim:] / trace.speed[-lim:])
        gearratio_collected = trace.gears[trace.gear_collected-1]
        
        #data['rpm'] is the drag corrected rpm over time per gear
        for data, gearratio in zip(self.geardata[1:], trace.gears):
            data['rpm'] = data['speed'] * (gearratio / gearratio_collected) * rpmspeedratio
        
        #add warning light if in a gear that is too low for the rpm
        #with a fudge factor of 10% to avoid blinking
        ratios = [y/x for x,y in zip(trace.gears[:-1], trace.gears[1:])]
        self.downshift_limit = [0,0] + [int(shiftrpm*ratio/1.1) for shiftrpm, ratio in zip(rpmtable[1:], ratios)] 
        self.logger.info(f'downshift limits: {self.downshift_limit}')
            
        self.calculate_state_triggers()

    def timeadjusted_rpm(self, framecount, rpm_start, rpmvalues):
        for j, x in enumerate(rpmvalues):
            if x >= rpm_start:
                offset = int(min(max(j - framecount, 0), len(rpmvalues)-1))
                return int(rpmvalues[offset])
                #print(f"j {j} val {rpmvalues[j]} offset {offset}")
        return int(rpmvalues[min(-framecount-1, -1)]) #if rpm_start not in rpmvalues, commonly used for revlimit

    def calculate_state_triggers(self):
        for gear, rpm in enumerate(self.rpmtable):
            if rpm == 0: #rpmtable has initial 0 and 0 for untested gears
                self.run_shiftleds[gear] = False
                continue
            self.run_shiftleds[gear] = True
                        
            #if at rev limit within x milliseconds, shift optimal shift point state to be x milliseconds away
            #scale graph to rev limit as to avoid issues with gears capping out below rev limit leading to a too low rpmlimit_ms
            adjusted_rpmlimit_ms = self.timeadjusted_rpm(V.distance_from_revlimit_ms.get(), 
                                                         self.revlimit, 
                                                         self.geardata[gear]['rpm']*(self.revlimit/self.geardata[gear]['rpm'][-1])) 
            adjusted_rpmlimit_abs = int(self.revlimit*V.distance_from_revlimit_pct.get())
            self.logger.info(f"{gear}: {rpm} rpmlimit ms:{adjusted_rpmlimit_ms}, abs: {adjusted_rpmlimit_abs}")
            
            adjusted_rpm = min(rpm, adjusted_rpmlimit_ms, adjusted_rpmlimit_abs)    
            overrev_rpm = self.timeadjusted_rpm(int(V.reaction_time.get() - V.illumination_interval.get()/5), #offset is negative
                                                adjusted_rpm, self.geardata[gear]['rpm'])
            revlimit_rpm = min(adjusted_rpmlimit_ms, adjusted_rpmlimit_abs)
            
            gear_table = self.state_table[gear]
            gear_table[STATE_REVLIMIT].set(revlimit_rpm)
            gear_table[STATE_OVERREV].set(overrev_rpm if overrev_rpm < revlimit_rpm else revlimit_rpm) #unhappy state
            gear_table[STATE_SHIFT].set(self.timeadjusted_rpm(V.reaction_time.get(), adjusted_rpm, self.geardata[gear]['rpm'])) #happy state
            self.audio_cue_rpm[gear] = self.timeadjusted_rpm(V.reaction_time_tone.get(), adjusted_rpm, self.geardata[gear]['rpm']) #happy state
            interval = int(V.illumination_interval.get()/(STATE_SHIFT-1)) #STATE_SHIFT-1 is the number of states for the ramp up
            for state in range(STATE_SHIFT-1, 0, -1):
                gear_table[state].set(self.timeadjusted_rpm(interval, gear_table[state+1].get(), self.geardata[gear]['rpm']))
                
        self.hysteresis_rpm = V.hysteresis_pct_revlimit.get()*self.revlimit
        if any(self.run_shiftleds):
            self.logger.info(f"hysteresis downwards at {self.hysteresis_rpm:.0f} rpm steps")
            self.logger.info(f'audio cues at {self.audio_cue_rpm}')
    
        #grey out gears that do not have a shift rpm
        for label_array, active in zip(self.trigger_labels, self.run_shiftleds[1:]):
            fg = constants.text_color if active else '#1A1A1A'
            for label in label_array:
                label.configure(fg=fg)

    def update_button(self, event):
        if (V.shiftlight_x.get() != self.window.winfo_x() or V.shiftlight_y.get() != self.window.winfo_y()):
            self.window.geometry(f"+{V.shiftlight_x.get()}+{V.shiftlight_y.get()}")
            self.logger.info(f"ledbar offset {V.shiftlight_x.get()} and {V.shiftlight_y.get()}")
        else:
            self.calculate_state_triggers()
        self.logger.info("update button hit!")
        with open(FILENAME_SETTINGS, 'w') as file:
            config.update(V._to_config())
            json.dump(config, file, indent=4)

    def update (self, fdp):
        self.update_lights_visibility(fdp)
        
        if fdp.is_race_on == 0:
            return
        
        gear = fdp.gear
        if gear == 0:
            gear = 'R'
        elif gear == 11:
            gear == 'N'
        self.gear_var.set(f'{gear}')
        
        if self.update_rpm_var: #update rate 30hz
            self.rpm_var.set(int(fdp.current_engine_rpm))
        self.update_rpm_var = not(self.update_rpm_var)
        
        if not self.run_shiftleds[fdp.gear]:
            if self.state != 0: #reset state for gears without leds
                self.state = 0
                self.update_leds(fdp)
            return
        
        #loop over state triggers in reverse order
        for state, shiftrpm in reversed(list(enumerate(self.state_table[fdp.gear]))):
            if fdp.current_engine_rpm >= shiftrpm.get():
                break
        
        #drop down in state only if drop in rpm is higher than hysteresis value
        #alternatively, drop down in state after x frames
        if state < self.state:
            if fdp.current_engine_rpm <= self.state_table[fdp.gear][self.state].get() - self.hysteresis_rpm:
                self.state = state
            # elif self.countdowntimer < V.state_dropdown_delay.get():
            #     self.countdowntimer += 1
            # else:
            #     self.state = state
        else:
            # self.countdowntimer = V.state_dropdown_delay.get() 
            self.state = state

        if self.log_shifts_var.get():
            self.handle_state_statistics(self.state, fdp)
            
        self.update_leds(fdp)
        
        if self.play_beep_var.get() and self.beep_counter <= 0:
            if fdp.current_engine_rpm > self.audio_cue_rpm[gear]:
                self.beep_counter = 20
                try:
                    winsound.PlaySound(config['audiofile'], 
                                       (winsound.SND_FILENAME | 
                                        winsound.SND_ASYNC | 
                                        winsound.SND_NODEFAULT))
                except:
                    self.logger.info("Sound failed to play")
            elif fdp.current_engine_rpm < math.ceil(0.75*self.audio_cue_rpm[gear]):
                self.beep_counter = 0
        elif self.beep_counter > 0 and fdp.current_engine_rpm < self.audio_cue_rpm[gear]:
            self.beep_counter -= 1

    def handle_state_statistics(self, state, fdp):
        self.deque.appendleft((state, fdp))
        if len(self.deque) == 1 or self.deque[0][1].gear <= self.deque[1][1].gear:
            return
        #gear changed, do work
        #run back to last frame with positive power (first frame of gear shift has negative power)
        #cut off points until most recent frame with state 0 if it exists
        #group consecutive states together, reverse the list
        states = [s for s,x in dropwhile(lambda y: y[1].power < 0, self.deque)]
        states = states[:states.index(0)-1] if 0 in states else states
        grouped = [f'{x}:{len(list(y)):2}' for x,y in groupby(reversed(states))]
        self.logger.info('|'.join(grouped))
        self.deque.clear()        
        
    def update_leds(self, fdp=None):
        gear = fdp.gear if fdp is not None else 1
        rpm = fdp.current_engine_rpm if fdp is not None else -1
            
        ledbar = STATES[self.state]
        for i in range(9):
            self.canvas.itemconfig(self.ledbar[i], fill=ledbar[i])
        
        #update last led to red if rpm is too low
        lastfill = ledbar[-1]
        if rpm > -1 and rpm <= self.downshift_limit[gear]:
            lastfill = Shiftlight.RED
        self.canvas.itemconfig(self.ledbar[-1], fill=lastfill)

    def update_lights_visibility(self, fdp=None):
        is_race_on = (fdp.is_race_on==1 and fdp.current_engine_rpm > math.ceil(fdp.engine_idle_rpm)) if fdp is not None else False
        user_toggle = self.display_lights_var.get()
        window_visible = (self.window.state() == 'normal')
        if window_visible and not(user_toggle and is_race_on):
            self.window.withdraw()
        elif user_toggle and is_race_on:
            self.window.deiconify()
        # if self.display_lights_var.get():
        #     self.window.deiconify()
        # else:
        #     self.window.withdraw()
            
    def update_gearnr_visibility(self):
        if self.display_gearnr_var.get():
            self.gear_label.pack()
        else:
            self.gear_label.pack_forget()

    def set_canvas(self, frame):
        self.set_config_canvas(frame)
        self.set_table_canvas(frame)

    def set_config_canvas(self, frame):
        self.frame_config = tkinter.Frame(frame, border=0, bg=constants.background_color, relief="groove",
                                            highlightthickness=True, highlightcolor=constants.text_color)
        
        opts = {'bg':constants.background_color, 'fg':constants.text_color, 'font':('Helvetica 12')}
        
        for row, v in enumerate(V._var_list()):
            tkinter.Label(self.frame_config, text=v.name, **opts).grid(row=row, column=0)
            tkinter.Entry(self.frame_config, textvariable=v.var, width=5, justify=tkinter.RIGHT, **opts).grid(row=row, column=1)
            tkinter.Label(self.frame_config, text=v.unit, **opts).grid(row=row, column=2)            
            
        tkinter.Label(self.frame_config, textvariable=self.rpm_var, bg=constants.background_color, fg=constants.text_color,
                      font=('Helvetica 18 bold')).grid(row=row+1)

        #TODO: grey out update button unless changes are made?
        button = tkinter.Button(self.frame_config, text='Update', bg=constants.background_color, fg=constants.text_color,
                                borderwidth=3, highlightcolor=constants.text_color, highlightthickness=True)
        button.bind('<Button-1>', self.update_button)
        button.grid(row=row+1, column=1)
        
        tkinter.Checkbutton(self.frame_config, text='Lights', variable=self.display_lights_var, 
                            command=self.update_lights_visibility, **opts).grid(row=0, column=3)
        tkinter.Checkbutton(self.frame_config, text='Gear', variable=self.display_gearnr_var,
                            command=self.update_gearnr_visibility, **opts).grid(row=1, column=3)
        tkinter.Checkbutton(self.frame_config, text='Tone', variable=self.play_beep_var, **opts).grid(row=2, column=3)
        
        tkinter.Checkbutton(self.frame_config, text='Log shifts', variable=self.log_shifts_var,
                            command=self.update_gearnr_visibility, **opts).grid(row=row+1, column=2, columnspan=2)
        
        
        self.frame_config.pack(fill='both', expand=True)
    
    def set_table_canvas(self, frame):
        self.frame_table = tkinter.Frame(frame, border=0, bg=constants.background_color, relief="groove",
                                            highlightthickness=True, highlightcolor=constants.text_color)
        opts = {'bg':constants.background_color, 'fg':constants.text_color, 'font':('Helvetica 12')}
        
        self.trigger_labels = []
        tkinter.Label(self.frame_table, text='Gear \ State', width=10, **opts).grid(row=0, column=0, sticky=tkinter.E)
        for state in range(1, len(STATES)):
            tkinter.Label(self.frame_table, text=state, width=5, **opts).grid(row=0, column=0+state, sticky=tkinter.N)
        for gear in range(1, 11):            
            tkinter.Label(self.frame_table, text=gear, width=5, **opts).grid(row=gear, column=0, sticky=tkinter.E)
            row_labels = []
            for state in range(1, len(STATES)):
                label = tkinter.Entry(self.frame_table, textvariable=self.state_table[gear][state], width=5, justify=tkinter.RIGHT, **opts)
                label.grid(row=gear, column=0+state)
                row_labels.append(label)
            self.trigger_labels.append(row_labels)
            
        self.frame_table.pack(fill='both', expand=True)

    def reset(self):
        self.state = 0
        # self.dropdowntimer = V.state_dropdown_delay.get()
        self.update_leds()
        
        self.deque.clear()
        
        self.update_rpm_var = True
        self.rpm_var.set(0)
        self.gear_var.set('1')
        self.run_shiftleds = [False for x in range(11)]
        [state.set(0) for row in self.state_table for state in row]        
        self.audio_cue_rpm = [0 for x in range(11)]
        self.rpmtable = [0 for x in range(11)]
        self.revlimit = 0
        self.calculate_state_triggers()
        
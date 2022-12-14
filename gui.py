import sys
import os
import tkinter
import tkinter.ttk
import warnings
import json #for importing config and data files
import statistics
import math

from tkinter import scrolledtext
from pynput.keyboard import Listener

# from https://pypi.org/project/pynput/
# section Ensuring consistent coordinates between listener and controller on Windows
import ctypes
PROCESS_PER_MONITOR_DPI_AWARE = 2
ctypes.windll.shcore.SetProcessDpiAwareness(PROCESS_PER_MONITOR_DPI_AWARE)

from scipy import interpolate
import matplotlib.pyplot as plt
import numpy as np

import constants
from dragderivation import Trace

from guimap import GUIMap, GUIMapDummy
from guiled import GUILed, GUILedDummy
from guisuspension import GUISuspension, GUISuspensionDummy
from guiwheelsize import GUIWheelsize, GUIWheelsizeDummy
from guilaptimes import GUILaptimes, GUILaptimesDummy
from guicarinfo import GUICarInfo, GUICarInfoDummy
from guilateralg import GUILateralG, GUILateralGDummy
from guibraketest import GUIBraketest, GUIBraketestDummy
from guilaunchtest import GUILaunchtest, GUILaunchtestDummy
from guigearstats import GUIGearStats, GUIGearStatsDummy

if not os.path.exists('traces'):
    os.makedirs('traces')

from forza import Forza
from concurrent.futures.thread import ThreadPoolExecutor
from logger import Logger, TextHandler


FILENAME_SETTINGS = 'settings_gui.json'
if len(sys.argv) > 1:
    FILENAME_SETTINGS = sys.argv[1]

DEFAULTCONFIG = {"window_offset_x": 0, "window_offset_y": 0, 
    'plugins':{
#    'frame_basic':{'enabled': False, 'anchor': 'NW', 'relx': 0.0, 'rely': 0.0}, #TODO: rewrite frame_basic to follow plugin format
    'map':        {'enabled': False, 'map_canvas':    {'anchor': 'nw', 'relx': 0.5,   'rely': 0.5}},
    'ledbar':     {'enabled': False, 'frame_config':  {'anchor': 'ne', 'relx': 1.0,   'rely': 0.0},
                                     'frame_table':   {'anchor': 'se', 'relx': 1.0,   'rely': 1.0}},
    'suspension': {'enabled': True,  'frame':         {'anchor': 'ne', 'relx': 1.0,   'rely': 0.0}},
    'wheelsize':  {'enabled': False, 'frame':         {'anchor': 'nw', 'relx': 0.0,   'rely': 0.0}},
    'laptimes':   {'enabled': False, 'frame':         {'anchor': 'nw', 'relx': 0.0,   'rely': 0.0}},
    'carinfo':    {'enabled': True,  'frame':         {'anchor': 'sw', 'relx': 0.0,   'rely': 1.0}},
    'lateralg':   {'enabled': True,  'frame':         {'anchor':  'w', 'relx': 0.325, 'rely': 0.63},
                                     'arrowframe':    {'anchor':  'n', 'relx': 0.40,  'rely': 0.0}},
    'braketest':  {'enabled': True,  'frame':         {'anchor':  'e', 'relx': 1.0,   'rely': 0.63}},
    'launchtest': {'enabled': True,  'frame':         {'anchor':  'w', 'relx': 0.0,   'rely': 0.64}},
    'gearstats':  {'enabled': True } } }
    
config = DEFAULTCONFIG
if os.path.exists(FILENAME_SETTINGS):
    with open(FILENAME_SETTINGS) as file:
        config.update(json.load(file))
else:
    print(f'filename {FILENAME_SETTINGS} does not exist, creating')
with open(FILENAME_SETTINGS, 'w') as file:
    json.dump(config, file, indent=4)
    
# suppress matplotlib warning while running in thread
warnings.filterwarnings("ignore", category=UserWarning)

'''
TODO:
- Move magical constants to a configuration file
- add Balloon tooltop to tickbox Draw torque graph
- draw map of circuit with left/right side
- move torque graph to a frame inside the window?
  https://splunktool.com/resizing-a-matplotlib-plot-in-a-tkinter-toplevel

-make use of styles to remove constant references to bg/fg colors
-make use of tkinter variables to remove awkward treeview assignments
-remove forza dependency
-figure out if socket can be closed cleanly
-abstract away from the large list of plugins to a dictionary
-rewrite treeview usage
-rewrite optimal shift rpm to use intersections not interpolated graphs

NOTES
fdp.dist_traveled seems broken for freeroam
reverse gear is not a fixed ratio. maybe fixed per transmissioN?
'''

class MainWindow:
    def __init__(self):
        """init
        """
        self.__init__window()
        self.__init__variables()
        
        self.set_log_frame()

        # forza info
        self.threadPool = ThreadPoolExecutor(max_workers=8, thread_name_prefix="exec")
        self.forza5 = Forza(self.threadPool, self.logger, constants.packet_format)
        self.listener = Listener(on_press=self.on_press)
        
        enabled = {key: value['enabled'] for key, value in config['plugins'].items()}
        self.map = GUIMap(self.logger) if enabled['map'] else GUIMapDummy(self.logger)
        self.ledbar = GUILed(self.logger, self.root) if enabled['ledbar'] else GUILedDummy(self.logger, self.root)
        self.suspension = GUISuspension(self.logger) if enabled['suspension'] else GUISuspensionDummy(self.logger)
        self.wheelsize = GUIWheelsize(self.logger) if enabled['wheelsize'] else GUIWheelsizeDummy(self.logger)
        self.laptimes = GUILaptimes(self.logger) if enabled['laptimes'] else GUILaptimesDummy(self.logger)
        self.carinfo = GUICarInfo(self.logger) if enabled['carinfo'] else GUICarInfoDummy(self.logger)
        self.lateralg = GUILateralG(self.logger) if enabled['lateralg'] else GUILateralGDummy(self.logger)
        self.braketest = GUIBraketest(self.logger) if enabled['braketest'] else GUIBraketestDummy(self.logger)
        self.launchtest = GUILaunchtest(self.logger) if enabled['launchtest'] else GUILaunchtestDummy(self.logger)
        self.gearstats = GUIGearStats(self.logger) if enabled['gearstats'] else GUIGearStatsDummy(self.logger)

        self.set_car_info_frame()
        self.set_car_perf_frame()
        self.set_shift_point_frame()
        self.set_button_frame()
        self.set_program_info_frame()
        
        self.root.protocol('WM_DELETE_WINDOW', self.close)
        self.logger.info('Forza Horizon 5: Statistics started')
        self.listener.start()
        self.root.mainloop()
    
    def __init__window(self):
        self.root = tkinter.Tk()
        
        self.root.tk.call('tk', 'scaling', 1.4) #Spyder console fix for DPI too low
        # Configure the rows that are in use to have weight #
        self.root.grid_rowconfigure(0, minsize=550, weight=550)
        self.root.grid_rowconfigure(1, minsize=300, weight=400)

        # Configure the cols that are in use to have weight #
        self.root.grid_columnconfigure(0, minsize=175, weight=175)
        self.root.grid_columnconfigure(1, minsize=625, weight=625)
        self.root.grid_columnconfigure(2, minsize=250, weight=250)

        self.root.title("ForzaGUI")
        self.root.geometry(f"1050x950+{config['window_offset_x']}+{config['window_offset_y']}")
        self.root.minsize(1050, 950)
        self.root.maxsize(1050, 950)
        self.root["background"] = constants.background_color
    
    def __init__variables(self):
        self.acceleration_var = tkinter.StringVar()
        self.acceleration_var.set("0.0%")
        self.brake_var = tkinter.StringVar()
        self.brake_var.set("0.0%")        
        self.steer_var = tkinter.StringVar()
        self.steer_var.set("0")        
        
        self.infovarlist = ('car_ordinal', 'car_class', 'car_performance_index',
                            'drivetrain_type', 'num_cylinders', 
                            'engine_max_rpm', 'engine_idle_rpm')
        
        self.extravarlist = ['revlimit', 'peak_power_kw', 'peak_torque_Nm', 'aspiration']
        
        self.infovar_tree = {}
        self.infovar_car_ordinal = None
        self.infovar_car_performance_index = None
        
        #self.prevrev = 0
        self.prevrev_torque = 0
        self.revlimit = 0

        self.collect_rpm = 0    
        self.trace = None
        self.rpmtable = [0 for x in range(1,11)]      
        
        self.torquegraph_var = tkinter.IntVar(value=0)
    
    def update_car_info(self, fdp):
        """update car info

        Args:
            fdp: fdp
        """
        if not self.forza5.isRunning:
            return
        
        if fdp.gear == 11: #gear 11 is neutral, hit when triggering events in the map
            return         #this breaks various hardcoded array limits
        
        #update variable section
        
        #wait for revs to increase
        if self.collect_rpm == 1:
            #self.logger.info(f"Waiting on throttle input {fdp.current_engine_rpm} vs {self.prevrev_torque}")
            if fdp.accel > 0 and fdp.current_engine_rpm > self.prevrev_torque:
                self.collect_rpm = 2
                self.trace = Trace(gear_collected=fdp.gear,
                                   gears=self.gearstats.gearratios)
        #collect data
        if self.collect_rpm == 2:
            #self.logger.info(f"{fdp.current_engine_rpm} vs {self.prevrev_torque}")
            if fdp.power > 0 and fdp.accel > 0: #fdp.current_engine_rpm > self.prevrev_torque:
                self.trace.add(fdp)
            else: #finish up and draw graph
                self.logger.info("Draw graph by pressing the Sweep (F8) button")
                self.trace.finish()
                self.add_carinfo_to_trace(fdp)
                self.trace.writetofile(f"traces/trace_ord{fdp.car_ordinal}_pi{fdp.car_performance_index}.json")
                self.collect_rpm = 0
                self.revlimit = self.trace.rpm[-1] #fdp.current_engine_rpm
                self.infotree.set('revlimit', column='var_value', value=int(self.revlimit))
                self.infotree.set('peak_power_kw', column='var_value', value=round(max(self.trace.power)))
                self.infotree.set('peak_torque_Nm', column='var_value', value=round(max(self.trace.torque)))
        self.prevrev_torque = fdp.current_engine_rpm

        # if fdp.power < 0 and fdp.accel > 0:
        #     self.revlimit = max(self.prevrev, self.revlimit)
        # elif fdp.power >= 0:
        #     self.prevrev = fdp.current_engine_rpm
        
        if self.infovar_car_ordinal != fdp.car_ordinal:
            self.reset_car_info()
            self.infovar_car_ordinal = fdp.car_ordinal
            self.infovar_car_performance_index = fdp.car_performance_index
            self.update_car_info_infovars(fdp)
            self.torquegraph_var.set(0)
            self.load_data(None)
            
        self.map.update(fdp)
        self.ledbar.update(fdp)     
        self.suspension.update(fdp)
        self.wheelsize.update(fdp)
        self.laptimes.update(fdp)
        self.carinfo.update(fdp)
        self.lateralg.update(fdp)
        self.braketest.update(fdp)
        self.launchtest.update(fdp)
        self.gearstats.update(fdp)
        
        #update display variables
        self.display_car_info(fdp)

    def display_car_info(self, fdp):
        self.acceleration_var.set(f"{str(round(fdp.accel / 255 * 100, 1))}%")
        self.brake_var.set(f"{str(round(fdp.brake / 255 * 100, 1))}%")
        self.steer_var.set(f"{fdp.steer}")
                
        self.suspension.display()
        self.wheelsize.display()
        self.laptimes.display()
        self.carinfo.display()
        self.lateralg.display()
        self.gearstats.display()
        #self.braketest.display()
        #self.launchtest.display()
     
    def update_car_info_infovars(self, fdp):
        infovars = dict(zip(self.infovarlist, fdp.to_list(self.infovarlist)))
        infovars['drivetrain_type'] = ['FWD', 'RWD', 'AWD'][infovars['drivetrain_type']]
        for key, value in infovars.items():
            self.infotree.set(key, column='var_value', value=value)

    def reset_car_info(self):
        """reset car info and tree view
        """
        # reset info variables
        for key in self.infotree.get_children():
            self.infotree.set(key, column='var_value', value='-')
        self.infovar_car_ordinal = None

        # reset accel and brake
        self.acceleration_var.set("0.0%")
        self.brake_var.set("0.0%")
        self.steer_var.set("0")
                        
        self.map.reset()
        self.ledbar.reset()
        self.suspension.reset()
        self.wheelsize.reset()
        self.laptimes.reset()
        self.carinfo.reset()
        self.lateralg.reset()
        self.gearstats.reset()
        self.braketest.reset()
        self.launchtest.reset()

        #self.prevrev = 0
        self.prevrev_torque = 0
        self.revlimit = 0
        
        self.car_ordinal = 0
        self.car_performance_index = 0
      
        self.collect_rpm = 0
        self.trace = None
        
        self.rpmtable = [0 for x in range(11)]

    def load_data(self, event):
        #self.logger.info("Load data button was pressed!")
        filename = f"traces/trace_ord{self.infovar_car_ordinal}_pi{self.infovar_car_performance_index}.json"
        if os.path.exists(filename):
            self.trace = Trace(fromfile=True, filename=filename)
            self.logger.info(f"loaded file {filename}")
            #self.logger.info(f"{self.trace.gear_collected} and {self.trace.gears}")
            self.trace.finish()
            self.revlimit = self.trace.rpm[-1]
            self.infotree.set('revlimit', column='var_value', value=int(self.revlimit))
            self.infotree.set('peak_power_kw', column='var_value', value=round(max(self.trace.power)))
            self.infotree.set('peak_torque_Nm', column='var_value', value=round(max(self.trace.torque)))
            self.gearstats.gearratios = [0] + self.trace.gears + [0]*(10 - len(self.trace.gears))
            self.gearstats.display()
            self.rpmtorque_handler(None)
        else:
            self.logger.info("File does not exist")
    
    def add_carinfo_to_trace(self, fdp):
        carinfo = {}
        carinfo = dict(zip(self.infovarlist, fdp.to_list(self.infovarlist)))
        carinfo['drivetrain_type'] = ['FWD', 'RWD', 'AWD'][carinfo['drivetrain_type']]
        if config['plugins']['wheelsize']['enabled']:
            carinfo['wheelsize_front'] = self.wheelsize.wheelsize_front_var.get()
            carinfo['wheelsize_rear'] = self.wheelsize.wheelsize_rear_var.get()
        carinfo['shiftdelay'] = self.gearstats.shiftdelay_median
        self.trace.add_to_carinfo(carinfo)

    def set_car_info_frame(self):
        """set car info frame
        """
        # place car info frame
        self.car_info_frame = tkinter.Frame(self.root, border=0, bg=constants.background_color, relief="groove",
                                            highlightthickness=True, highlightcolor=constants.text_color)
        
        style = tkinter.ttk.Style()
        style.theme_use("clam")

        #set background and foreground of the treeview
        style.configure("Treeview",
                        background=constants.background_color,
                        foreground=constants.text_color,
                        fieldbackground=constants.background_color)
        style.map('Treeview', background=[('selected', '#BFBFBF')], foreground=[('selected', 'black')],
                  fieldbackground=[('selected', 'black')])


        columns = ('var_name', 'var_value')
        self.infotree = tkinter.ttk.Treeview(self.car_info_frame, columns=columns, show='headings', style='Treeview')
        
        self.infotree.heading('var_name', text="Variable")
        self.infotree.heading('var_value', text="Value")
        self.infotree.column('var_name', width=110, anchor=tkinter.CENTER)
        self.infotree.column('var_value', width=40, anchor=tkinter.CENTER)
        
        for var in self.infovarlist:
            self.infotree.insert('', tkinter.END, iid=var, values=(var,'-'))
        
        for var in self.extravarlist:
            self.infotree.insert('', tkinter.END, iid=var, values=(var,'-'))
        
        button = tkinter.Checkbutton(self.car_info_frame, text='Draw torque graph', variable=self.torquegraph_var, 
                            bg=constants.background_color, fg=constants.text_color,
                            onvalue=1, offvalue=0)

        self.load_data_button = tkinter.Button(self.car_info_frame, text='Load torque/ratios', bg=constants.background_color, fg=constants.text_color,
                                borderwidth=3, highlightcolor=constants.text_color, highlightthickness=True)
        self.load_data_button.bind('<Button-1>', self.load_data)
        
        
        self.infotree.pack(fill="both", expand=True)
        button.pack()
        self.load_data_button.pack()

        self.car_info_frame.grid(row=0, column=0, sticky='news')
        
    def set_car_perf_frame(self):
        """set car perf frame
        """
        # Place car perf frame
        self.car_perf_frame = tkinter.Frame(self.root, border=0, bg=constants.background_color, relief="groove",
                                            highlightthickness=True, highlightcolor=constants.text_color)
        self.car_perf_frame.grid(row=0, column=1, sticky='news', columnspan=2)
        self.car_perf_frame.update() #is this necessary?

        self.frame_basic = tkinter.Frame(self.car_perf_frame, border=0, bg=constants.background_color, relief="groove",
                                            highlightthickness=True, highlightcolor=constants.text_color)
        opts = {'bg':constants.background_color, 'fg':constants.text_color}
        # place acceleration information text
        tkinter.Label(self.frame_basic, text="Accel", font=('Helvetica 15 bold'), **opts).pack()
        tkinter.Label(self.frame_basic, textvariable=self.acceleration_var, width=6, 
                      anchor=tkinter.E, font=('Helvetica 35 bold italic'), **opts).pack()

        # place brake information test
        tkinter.Label(self.frame_basic, text="Brake", **opts, font=('Helvetica 15 bold')).pack()
        tkinter.Label(self.frame_basic, textvariable=self.brake_var, width=6, 
                      anchor=tkinter.E, font=('Helvetica 35 bold italic'), **opts).pack()
        
        tkinter.Label(self.frame_basic, text="Steer", **opts, font=('Helvetica 15 bold')).pack()
        tkinter.Label(self.frame_basic, textvariable=self.steer_var, width=6, 
                      anchor=tkinter.E, font=('Helvetica 30 bold italic'), **opts).pack()
                                             
        self.map.set_canvas(self.car_perf_frame)
        self.suspension.set_canvas(self.car_perf_frame)
        self.wheelsize.set_canvas(self.car_perf_frame)
        self.laptimes.set_canvas(self.car_perf_frame)
        self.carinfo.set_canvas(self.car_perf_frame)
        self.lateralg.set_canvas(self.car_perf_frame)
        self.braketest.set_canvas(self.car_perf_frame)
        self.launchtest.set_canvas(self.car_perf_frame)
        self.ledbar.set_canvas(self.car_perf_frame)
        
        self.frame_basic.place(anchor=tkinter.NW, relx=0.0, rely=0.0) 
        
        for name, plugin in config['plugins'].items():
            if not plugin['enabled']:
                continue
            frames = {k: v for k, v in plugin.items() if k != 'enabled'}
            for framename, values in frames.items():
                var = getattr(self, name)
                canvas = getattr(var, framename)
                canvas.place(anchor=values['anchor'], relx=values['relx'],
                             rely=values['rely'])
            else: #case multiple frames
                pass
                                                                                       
    def set_shift_point_frame(self):
        """set shift point frame
        """
        # place shift point frame
        pass
        # self.shift_point_frame = tkinter.Frame(self.root, border=0, relief="groove",
        #                                        background=constants.background_color,
        #                                        highlightthickness=True, highlightcolor=constants.text_color)

        # self.shift_point_frame.grid(row=0, column=2, sticky='news')

    def set_button_frame(self):
        """set buttom frame
        """
        # place button frame
        self.button_frame = tkinter.Frame(self.root, border=0, bg=constants.background_color, relief="groove",
                                          highlightthickness=True, highlightcolor=constants.text_color)

        button_names = [('Connect', self.collect_data_handler, constants.collect_data),
                        ('Collect ratios', self.gatherratios_handler, constants.gatherratios),
                        ('Sweep', self.rpmtorque_handler, constants.analysis),
                        ('Reset', self.reset_handler, constants.auto_shift)]
        
        # if config['plugins']['carinfo']['enabled']:
        #     button_names.insert(0, ('Write CSV', self.writeback_handler, constants.writeback))

        for i, (name, func, shortcut) in enumerate(button_names):
            button = tkinter.Button(self.button_frame, text=f'{name} ({shortcut.name})',
                                    bg=constants.background_color, fg=constants.text_color, borderwidth=3,
                                    highlightcolor=constants.text_color, highlightthickness=True)
            button.bind('<Button-1>', func)
            button.place(relx=0.5, rely=1 / len(button_names) * i + 1 / len(button_names) / 2, relwidth=0.8,
                         relheight=1 / len(button_names) * 0.9, anchor='center')

        self.button_frame.grid(row=1, column=0, sticky='news')

    def set_log_frame(self):
        """set log frame
        """
        # place log frame
        self.log_frame = tkinter.Frame(self.root, border=0, bg=constants.background_color, relief="groove",
                                       highlightthickness=True, highlightcolor=constants.text_color)

        log = tkinter.scrolledtext.ScrolledText(self.log_frame, bg=constants.background_color, borderwidth=2,
                                                font='Monaco 9 bold', fg=constants.text_color)
        log.pack(fill="both", expand=True)
        log_handler = TextHandler(log)
        self.logger = (Logger(log_handler))('ForzaHorizon5')

        button = tkinter.Button(self.log_frame, text='Clear', bg=constants.background_color, fg=constants.text_color,
                                borderwidth=3, highlightcolor=constants.text_color, highlightthickness=True)
        button.bind('<Button-1>', lambda x: log.delete(1.0, 'end'))
        button.place(relx=0.93, rely=0.053, relwidth=0.05, relheight=0.05, anchor='center', bordermode='inside')
        self.log_frame.grid(row=1, column=1, sticky='news')

    def set_program_info_frame(self):
        """set code info frame
        """
        # place code info frame
        self.program_info_frame = tkinter.Frame(self.root, border=0, bg=constants.background_color,
                                                relief="groove",
                                                highlightthickness=True, highlightcolor=constants.text_color)
        self.gearstats.set_canvas(self.program_info_frame)
        self.program_info_frame.grid(row=1, column=2, sticky='news')

    def collect_data_handler(self, event):
        """collect data button callback

        Args:
            event
        """
        if self.forza5.isRunning:
            self.logger.info('stopping monitoring')

            def stopping():
                self.forza5.isRunning = False
                self.reset_car_info()

            self.threadPool.submit(stopping)
        else:
            self.logger.info('starting monitoring')

            def starting():
                self.forza5.isRunning = True
                self.forza5.test_gear(self.update_car_info)

            self.threadPool.submit(starting)
            
#TODO: split calculation and graphing into separate functions
    def rpmtorque_handler(self, event):
        #log data (through update_car_info) if no data exists
        if self.trace is None:
            self.collect_rpm = 1
            self.logger.info("Logging rpm/torque/power")
            return
        
        self.collect_rpm = 0
        self.logger.info("Doing maths")
        
        rpm = self.trace.rpm
        torque = self.trace.torque
        power = self.trace.power #power in kw
        speed = self.trace.speed #speed in kmh
                    
        gears = [self.gearstats.gearratios[key] for key in range(1,11) if self.gearstats.gearratios[key] != 0]
        ratios = [gears[x]/gears[x+1] for x in range(len(gears)-1)]
        
        self.logger.info([round(g, 3) for g in gears])
        self.logger.info([round(r, 3) for r in ratios])
        
        #find intersection point of the adjusted power graph per two subsequent gears if it exists
        for i, ratio in enumerate(ratios):
            f = interpolate.interp1d(rpm, power)
            g = interpolate.interp1d([x*ratio for x in rpm], power)
            if f(rpm[-1]) > g(rpm[-1]): #if the final point of gear x > gear x+1, return max
                shiftrpm = int(rpm[-1])
            else:
                distances = [abs(f(x)-g(x)) for x in range(int(rpm[0]*ratio)+1, int(max(rpm)))]
                index = distances.index(min(distances))
                shiftrpm = int(index+rpm[0]*ratio+1)
            self.rpmtable[i+1] = shiftrpm
            self.logger.info(f"{i+1}: shift rpm {shiftrpm}, drop to {int(shiftrpm/ratio)}, "
                  f"drop is {int(shiftrpm*(1.0 - 1.0/ratio))}")

        self.logger.info(list(enumerate(self.rpmtable)))
        self.ledbar.set_rpmtable(self.rpmtable, self.revlimit, self.trace)
        self.gearstats.set_rpmtable(self.rpmtable)
        
        if self.torquegraph_var.get() == 0:
            return
        
        #val is the median ratio of rpm and speed scaled to the final ratio
        val = statistics.median([(a/b) for (a, b) in zip(rpm, speed)])*gears[-1]/gears[self.trace.gear_collected-1]
        
        plt.close()
        plt.ion()
        plt.rcParams["font.family"] = "monospace" #change legend font to monospace for number alignment
        fig, ax = plt.subplots()
        fig.set_size_inches(12, 10)
        
        shiftrpms = self.rpmtable[1:] + [0]
        for i, (g, s) in enumerate(zip(gears, shiftrpms)):
            if i+1 == len(gears):
                label = f'{i+1:>2}  maxspeed {rpm[-1]/val:5.1f}'
            else:
                label = f'{i+1:>2} {s:>9} {gears[-1]*s/(val*g):>10.1f}'
            ax.plot([gears[-1]*x/g for x in rpm], [t*g for t in torque], 
                    label=label)  
        
        #draw the vertical lines for shift speeds
        ymin, ymax = ax.get_ylim()
        for g, s in zip(gears, shiftrpms):
            ax.vlines(gears[-1]*s/g, 0, ymax, linestyle=':')
        
        ax.legend(title='     Gear   shiftrpm   shift at')
        
        ax.grid()
        ax.set_xlabel("rpm")
        ax.set_ylabel("torque (N.m)")
        
        ax2 = ax.secondary_xaxis("top")
        ax2.set_xlabel("speed (km/h)")
        
        rpmmax = math.ceil(rpm[-1]/500)*500
        xticks = np.arange(0,rpmmax+500,500)
        
        ax.set_ylim(0, ymax)
        ax.set_xlim(0, rpmmax)
        
        ax.set_xticks(xticks)
        ax2.set_xticks(xticks)
        ax2.set_xticklabels([round(x/val,1) for x in xticks])
        
        fig.tight_layout()
        plt.show()


    def gatherratios_handler(self, event):
        self.gearstats.gatherratios = not(self.gearstats.gatherratios)
        if self.gearstats.gatherratios:
            self.logger.info("Updating ratios")
        else:
            self.logger.info("Ratios not updating")

    def reset_handler(self, event):
        """ run reset callback
        
        Args:
            event
        """
        self.reset_car_info()
        
    def writeback_handler(self, event):
        """ run writeback callback
        
        Args:
            event
        """
        #self.logger.info("Writing {}".format(self.carinfo.row))
        self.carinfo.writeback()

    def exit_handler(self, event):
        """exit button callback

        Args:
            event
        """
        shutdown(self.forza5, self.threadPool, self.listener)
        self.forza5.logger.info('bye~')
        self.root.destroy()


    def on_press(self, key):
        """on press callback

        Args:
            key: key
        """
        if key == constants.collect_data:
            self.collect_data_handler(None)
        elif key == constants.analysis:
            self.rpmtorque_handler(None)
            #self.analysis_handler(None, performance_profile=False, is_guid=False)
        elif key == constants.auto_shift:
            self.reset_handler(None)
        elif key == constants.gatherratios:
            self.gatherratios_handler(None)
        # elif key == constants.writeback and config['plugins']['carinfo']['enabled']:
        #     self.writeback_handler(None)
        #elif key == constants.stop:
        #    self.pause_handler(None)
        #elif key == constants.close:
        #    self.exit_handler(None)

    def close(self):
        """close program
        """
        shutdown(self.forza5, self.threadPool, self.listener) 
        self.root.destroy()

def shutdown(forza: Forza, threadPool: ThreadPoolExecutor, listener: Listener):
    """shutdown/clean up resources

    Args:
        forza (Forza): forza
        threadPool (ThreadPoolExecutor): thread pool
        listener (Listener): keyboard listener
    """
    forza.isRunning = False
    forza.server_socket.close()
    threadPool.shutdown(wait=False)
    listener.stop()

def main():
    """main.....
    """
    MainWindow()


if __name__ == "__main__":
    main()

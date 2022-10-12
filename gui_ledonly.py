import sys
import tkinter
import tkinter.ttk
import warnings
from tkinter import scrolledtext

from pynput.keyboard import Listener

#from collections import deque
import statistics
#from math import pi
import math

from scipy import interpolate

import matplotlib.pyplot as plt
import numpy as np

import constants
#import keyboard_helper

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

sys.path.append(r'./forza_motorsport')

#import helper
from forza import Forza
from concurrent.futures.thread import ThreadPoolExecutor
from logger import Logger, TextHandler

#map xor (suspension or led)
MAP = False
LED = True
WHEELSIZE = False
LAPTIMES = False

SUSPENSION = False
CARINFO = False
LATERALG = False
BRAKETEST = False
LAUNCHTEST = False
GEARSTATS = True

# suppress matplotlib warning while running in thread
warnings.filterwarnings("ignore", category=UserWarning)

'''
TODO:
- draw map of circuit with left/right side
- gather points for acceleration graph (on flat ground)

-add lateral g per velocity
--gather points: latg, speed, tire grip
--draw graph?

-remove forza dependency

-figure out if socket can be closed cleanly

-abstract away from the large list of plugins to a dictionary

test if the traction frontier is more square under braking
but i guess mash abs and mash the steering, maybe at various levels of abs

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
        self.forza5 = Forza(self.threadPool, self.logger, constants.packet_format, clutch=constants.enable_clutch)
        self.listener = Listener(on_press=self.on_press)
        
        self.map = GUIMap(self.logger) if MAP else GUIMapDummy(self.logger)
        self.ledbar = GUILed(self.logger) if LED else GUILedDummy(self.logger)
        self.suspension = GUISuspension(self.logger) if SUSPENSION else GUISuspensionDummy(self.logger)
        self.wheelsize = GUIWheelsize(self.logger) if WHEELSIZE else GUIWheelsizeDummy(self.logger)
        self.laptimes = GUILaptimes(self.logger) if LAPTIMES else GUILaptimesDummy(self.logger)
        self.carinfo = GUICarInfo(self.logger) if CARINFO else GUICarInfoDummy(self.logger)
        self.lateralg = GUILateralG(self.logger) if LATERALG else GUILateralGDummy(self.logger)
        self.braketest = GUIBraketest(self.logger) if BRAKETEST else GUIBraketestDummy(self.logger)
        self.launchtest = GUILaunchtest(self.logger) if LAUNCHTEST else GUILaunchtestDummy(self.logger)
        self.gearstats = GUIGearStats(self.logger) if GEARSTATS else GUIGearStatsDummy(self.logger)

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
        self.root.grid_rowconfigure(1, minsize=300, weight=300)

        # Configure the cols that are in use to have weight #
        self.root.grid_columnconfigure(0, minsize=175, weight=175)
        self.root.grid_columnconfigure(1, minsize=625, weight=625)
        self.root.grid_columnconfigure(2, minsize=250, weight=250)

        self.root.title("Forza Horizon 5: Totally Work-in-progress something stats")
        self.root.geometry("1050x850+-1208+0")
        self.root.minsize(1050, 850)
        self.root.maxsize(1050, 850)
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
        
        self.infovar_tree = {}
        self.infovar_car_ordinal = None
        
        self.prevrev = 0
        self.prevrev_torque = 0
        self.shiftlimit = 0
        self.revlimit_counter = 0
        self.revlimit = 0

        self.peak_power = None
        self.peak_torque = None

        self.collect_rpm = 0
        self.rpmtorque = []
        self.collectedingear = 0
        
        self.rpmtable = [0 for x in range(1,11)]       
    
    def update_car_info(self, fdp):
        """update car info

        Args:
            fdp: fdp
        """
        if not self.forza5.isRunning:
            return
                
        #update variable section
        
        #wait for revs to increase
        if self.collect_rpm == 1:
            #self.logger.info(f"Waiting on throttle input {fdp.current_engine_rpm} vs {self.prevrev_torque}")
            if fdp.accel > 0 and fdp.current_engine_rpm > self.prevrev_torque:
                self.collect_rpm = 2
                self.collectedingear = fdp.gear
        #collect data
        if self.collect_rpm == 2:
            #self.logger.info(f"{fdp.current_engine_rpm} vs {self.prevrev_torque}")
            if fdp.power > 0 and fdp.accel > 0: #fdp.current_engine_rpm > self.prevrev_torque:
                self.rpmtorque.append((fdp.current_engine_rpm, 
                                       fdp.torque,
                                       fdp.power/1000.0,
                                       fdp.speed,
                                       fdp.acceleration_z))
            else: #finish up and draw graph
                self.logger.info("Draw graph BY PRESSING THE GODDAMN BUTTON")
                with open("rpmtorqueraw.txt", "w") as file:
                    file.write(str(self.rpmtorque))
                #self.logger.info(self.rpmtorque)
                self.collect_rpm = 0
                self.infotree.item(self.peak_power, values=('peak_power_kw', round(max([x[2] for x in self.rpmtorque])), 1))
                self.infotree.item(self.peak_torque, values=('peak_torque_Nm', round(max([x[1] for x in self.rpmtorque])), 1))

        if fdp.power < 0 and fdp.accel > 0:
            self.revlimit = max(self.prevrev, self.revlimit)
        elif fdp.power >= 0:
            self.prevrev = fdp.current_engine_rpm
        self.prevrev_torque = fdp.current_engine_rpm
        
        if self.infovar_car_ordinal != fdp.car_ordinal:
            self.infovar_car_ordinal = fdp.car_ordinal
            self.update_car_info_infovars(fdp)
        
        self.map.update(fdp)
        self.ledbar.update(fdp)     
        self.suspension.update(fdp)
        self.wheelsize.update(fdp)
        self.laptimes.update(fdp)
        self.carinfo.update(fdp, self.revlimit, self.gearstats.get_shiftlimit()) #shiftlimit
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
        
        if self.revlimit_counter == 240: #limit update frequency to once per four seconds
            self.infotree.item(self.revlimit_var, values=('revlimit',int(self.revlimit)))
            self.revlimit_counter = 0
        else:
            self.revlimit_counter += 1
    #    self.infotree.item(self.shiftlimit_var, values=('shiftlimit','-'))#int(self.revlimit)))
        
        self.suspension.display()
        self.wheelsize.display()
        self.laptimes.display()
        self.carinfo.display()
        self.lateralg.display()
        self.gearstats.display()
        #self.braketest.display()
        #self.launchtest.display()
     
    def update_car_info_infovars(self, fdp):
        infovarlist_fdp = fdp.to_list(self.infovarlist)
        for i, value in enumerate(infovarlist_fdp):
            key = self.infovarlist[i]
            if key == "drivetrain_type":
                value = ['FWD', 'RWD', 'AWD'][value]
            self.infotree.item(self.infovar_tree[key], values=(key,value))

    def reset_car_info(self):
        """reset car info and tree view
        """
        
        # reset info variables
        for key in self.infovar_tree.keys():
            self.infotree.item(self.infovar_tree[key], values='-')
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
        self.laptimes.reset()
        self.lateralg.reset()
        self.gearstats.reset()
        self.braketest.reset()
        self.launchtest.reset()

        self.prevrev = 0
        self.prevrev_torque = 0
        self.revlimit = 0
        self.revlimit_counter = 0
        self.shiftlimit = 0
        
        self.infotree.item(self.peak_power, values=('peak_power_kw', '-'))
        self.infotree.item(self.peak_torque, values=('peak_torque_Nm', '-'))
      
        self.collect_rpm = 0
        self.rpmtorque = []
        self.rpmspeed = []
        
        self.rpmtable = [0 for x in range(11)]
        

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
            self.infovar_tree[var] = self.infotree.insert('', tkinter.END, text=var, values=(var,'-'))
            
        self.revlimit_var = self.infotree.insert('', tkinter.END, text='revlimit', values=('revlimit','-'))
        self.shiftlimit_var = self.infotree.insert('', tkinter.END, text='shiftlimit', values=('shiftlimit','-'))
        self.peak_power = self.infotree.insert('', tkinter.END, text='peak_power_kw', values=('peak_power_kw','-'))
        self.peak_torque = self.infotree.insert('', tkinter.END, text='peak_torque_Nm', values=('peak_torque_Nm','-'))
        
        self.infotree.pack(fill="both", expand=True)
        
        self.car_info_frame.grid(row=0, column=0, sticky='news')
        
    def set_car_perf_frame(self):
        """set car perf frame
        """
        # Place car perf frame
        self.car_perf_frame = tkinter.Frame(self.root, border=0, bg=constants.background_color, relief="groove",
                                            highlightthickness=True, highlightcolor=constants.text_color)
        self.car_perf_frame.grid(row=0, column=1, sticky='news')
        self.car_perf_frame.update() #is this necessary?


        self.frame_basic = tkinter.Frame(self.car_perf_frame, border=0, bg=constants.background_color, relief="groove",
                                            highlightthickness=True, highlightcolor=constants.text_color)
        # place acceleration information text
        tkinter.Label(self.frame_basic, text="Accel", bg=constants.background_color, fg=constants.text_color, 
                      font=('Helvetica 15 bold')).pack()
        tkinter.Label(self.frame_basic, textvariable=self.acceleration_var, bg=constants.background_color, width=6, anchor=tkinter.E,
                      fg=constants.text_color, font=('Helvetica 35 bold italic')).pack()

        # place brake information test
        tkinter.Label(self.frame_basic, text="Brake", bg=constants.background_color, fg=constants.text_color,
                      font=('Helvetica 15 bold')).pack()
        tkinter.Label(self.frame_basic, textvariable=self.brake_var, bg=constants.background_color, width=6, anchor=tkinter.E,
                      fg=constants.text_color, font=('Helvetica 35 bold italic')).pack()
        
        tkinter.Label(self.frame_basic, text="Steer", bg=constants.background_color, fg=constants.text_color,
                      font=('Helvetica 15 bold')).pack()
        tkinter.Label(self.frame_basic, textvariable=self.steer_var, bg=constants.background_color, width=6, anchor=tkinter.E,
                      fg=constants.text_color, font=('Helvetica 30 bold italic')).pack()
                                             
        self.map.set_canvas(self.car_perf_frame)
        self.suspension.set_canvas(self.car_perf_frame)
        self.wheelsize.set_canvas(self.car_perf_frame)
        self.laptimes.set_canvas(self.car_perf_frame)
        self.carinfo.set_canvas(self.car_perf_frame)
        self.lateralg.set_canvas(self.car_perf_frame)
        self.braketest.set_canvas(self.car_perf_frame)
        self.launchtest.set_canvas(self.car_perf_frame)
        self.ledbar.set_canvas(self.car_perf_frame)
        
        #self.carinfo.frame.place(       anchor=tkinter.SW,  relx=0.0 ,  rely=1.0)
        self.frame_basic.place(         anchor=tkinter.NW,  relx=0.0 ,  rely=0.0) 
        #self.launchtest.frame.place(    anchor=tkinter.W,   relx=0.0 ,  rely=0.64)
        #self.braketest.frame.place(     anchor=tkinter.E,   relx=1.00,  rely=0.63) 
        #self.lateralg.frame.place(      anchor=tkinter.W,   relx=0.325, rely=0.63) 
        #self.lateralg.arrowframe.place( anchor=tkinter.N,   relx=0.40 , rely=0.0) 
        #self.suspension.frame.place(    anchor=tkinter.NE,  relx=1.0,   rely=0.0) 
        self.ledbar.frame.place(        anchor=tkinter.S,   relx=0.5,   rely=1.00, width=500, height=90)
                                                                                       
    def set_shift_point_frame(self):
        """set shift point frame
        """
        # place shift point frame
        self.shift_point_frame = tkinter.Frame(self.root, border=0, relief="groove",
                                               background=constants.background_color,
                                               highlightthickness=True, highlightcolor=constants.text_color)

        self.gearstats.set_canvas(self.shift_point_frame)
        self.shift_point_frame.grid(row=0, column=2, sticky='news')

    def set_button_frame(self):
        """set buttom frame
        """
        # place button frame
        self.button_frame = tkinter.Frame(self.root, border=0, bg=constants.background_color, relief="groove",
                                          highlightthickness=True, highlightcolor=constants.text_color)

        button_names = [('Collect Data', self.collect_data_handler, constants.collect_data),
                        ('Collect ratios', self.gatherratios_handler, constants.gatherratios),
                        #('Analysis', self.analysis_handler, constants.analysis),
                        ('RPM/Torque', self.rpmtorque_handler, constants.analysis),
                        ('Reset', self.reset_handler, constants.auto_shift)]
                        #('Pause', self.pause_handler, constants.stop),
                        #('Exit', self.exit_handler, constants.close)]
        
        if CARINFO:
            button_names.insert(0, ('Write CSV', self.writeback_handler, constants.writeback))

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
        label = tkinter.Label(self.program_info_frame, text='RTB work in progress GUI for Forza remote telemetry. '
                                                            'derived from https://github.com/Juice-XIJ/forza_auto_gear',
                              bg=constants.background_color, borderwidth=2, fg=constants.text_color,
                              relief="groove", anchor="nw", justify=tkinter.LEFT)
        label.bind('<Configure>', lambda e: label.config(wraplength=int(label.winfo_width() * 0.9)))
        label.pack(fill="both", expand=True)
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
        if len(self.rpmtorque) == 0:
            self.collect_rpm = 1
            self.logger.info("Logging rpm/torque/power")
            return
        
        self.collect_rpm = 0
        self.logger.info("Drawing graph")
        
        rpm = [x[0] for x in self.rpmtorque]
        torque = [x[1] for x in self.rpmtorque]
        power = [x[2] for x in self.rpmtorque] #power in kw
        speed = [x[3]*3.6 for x in self.rpmtorque] #speed in kmh
                    
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

        #val is the median ratio of rpm and speed scaled to the final ratio
        val = statistics.median([(a/b) for (a, b) in zip(rpm, speed)])*gears[-1]/gears[self.collectedingear-1]
        
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

        self.logger.info(list(enumerate(self.rpmtable)))
        self.ledbar.set_rpmtable(self.rpmtable, rpm, gears, self.revlimit, self.collectedingear)
        self.gearstats.set_rpmtable(self.rpmtable)

    def gatherratios_handler(self, event):
        self.gearstats.gatherratios = not(self.gearstats.gatherratios)
        if self.gearstats.gatherratios:
            self.logger.info("Updating ratios")
        else:
            self.logger.info("Ratios not updating")

    # def analysis_handler(self, event, performance_profile=True, is_guid=True):
    #     """analysis button callback

    #     Args:
    #         event
    #         performance_profile (bool, optional): draw performance of not. Defaults to True.
    #         is_guid (bool, optional): is guid or not. Defaults to True.
    #     """
    #     if len(self.forza5.records) <= 0:
    #         self.logger.info(f'load config {constants.example_car_ordinal}.json for analysis as an example')
    #         helper.load_config(self.forza5,
    #                            os.path.join(constants.root_path, 'example', f'{constants.example_car_ordinal}.json'))
    #     self.logger.info('Analysis')

    #     self.forza5.analyze(performance_profile=performance_profile, is_gui=is_guid)
    #     self.update_tree()

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

    def run_handler(self, event):
        """run button callback

        Args:
            event
        """
        if self.forza5.isRunning:
            self.forza5.logger.info('stopping auto gear')

            def stopping():
                self.forza5.isRunning = False
                self.reset_car_info()

            self.threadPool.submit(stopping)
        else:
            self.forza5.logger.info('starting auto gear')

            def starting():
                self.forza5.isRunning = True
                self.forza5.run(self.update_tree, self.update_car_info)

            self.threadPool.submit(starting)

    # def pause_handler(self, event):
    #     """pause button callback

    #     Args:
    #         event
    #     """
    #     shutdown(self.forza5, self.threadPool, self.listener)
    #     self.reset_car_info()
    #     self.threadPool = ThreadPoolExecutor(max_workers=8, thread_name_prefix="exec")
    #     self.forza5.threadPool = self.threadPool
    #     self.listener = Listener(on_press=self.on_press)
    #     self.listener.start()
    #     self.forza5.logger.info('stopped')

    def exit_handler(self, event):
        """exit button callback

        Args:
            event
        """
        shutdown(self.forza5, self.threadPool, self.listener)
        self.forza5.logger.info('bye~')
        #self.forza5.server_socket.close() #spyder console fix: port in use on reopening gui.py
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
        elif key == constants.writeback and CARINFO:
            self.writeback_handler(None)
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
    #forza.server_socket.close()
    threadPool.shutdown(wait=False)
    listener.stop()

def main():
    """main.....
    """
    MainWindow()


if __name__ == "__main__":
    main()

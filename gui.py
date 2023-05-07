import sys
import os
import tkinter
import tkinter.ttk
import warnings
import json #for importing config and data files
import statistics
import math

import intersect

from tkinter import scrolledtext
from pynput.keyboard import Listener

# from https://pypi.org/project/pynput/
# section Ensuring consistent coordinates between listener and controller on Windows
import ctypes
PROCESS_PER_MONITOR_DPI_AWARE = 2
ctypes.windll.shcore.SetProcessDpiAwareness(PROCESS_PER_MONITOR_DPI_AWARE)

#from scipy import interpolate
import matplotlib.pyplot as plt
import numpy as np

#plugins
from guibasic import GUIBasic
from guimap import GUIMap
from guiled import GUILed
from guisuspension import GUISuspension
from guiwheelsize import GUIWheelsize
from guilaptimes import GUILaptimes
from guicarinfo import GUICarInfo
from guilateralg import GUILateralG
from guibraketest import GUIBraketest
from guilaunchtest import GUILaunchtest
from guigearstats import GUIGearStats

import constants
from dragderivation import Trace
from forza import Forza
from concurrent.futures.thread import ThreadPoolExecutor
from logger import Logger, TextHandler

if not os.path.exists('traces'):
    os.makedirs('traces')

FILENAME_SETTINGS = 'settings_gui.json'
if len(sys.argv) > 1:
    FILENAME_SETTINGS = sys.argv[1]

DEFAULTCONFIG = {"window_offset_x": 0, "window_offset_y": 0, 
    'plugins':{
    'basic':      {'enabled': True,  'frame':         {'anchor': 'ne', 'relx': 0.47,  'rely': 0.06}},
    'map':        {'enabled': False, 'map_canvas':    {'anchor': 'nw', 'relx': 0.50,  'rely': 0.50}},
    'ledbar':     {'enabled': True,  'frame_config':  {'anchor': 'se', 'relx': 1.00,  'rely': 1.00},
                                     'frame_table':   {'anchor': 'ne', 'relx': 1.00,  'rely': 0.06}},
    'suspension': {'enabled': False, 'frame':         {'anchor': 'ne', 'relx': 1.00,  'rely': 0.00}},
    'wheelsize':  {'enabled': True,  'frame':         {'anchor':  'e', 'relx': 1.00,  'rely': 0.54}},
    'laptimes':   {'enabled': False, 'frame':         {'anchor': 'nw', 'relx': 0.00,  'rely': 0.00}},
    'carinfo':    {'enabled': True,  'frame':         {'anchor': 'nw', 'relx': 0.00,  'rely': 0.00}},
    'lateralg':   {'enabled': True,  'frame':         {'anchor':  'w', 'relx': 0.00,  'rely': 0.64},
                                     'arrowframe':    {'anchor': 'ne', 'relx': 0.58,  'rely': 0.06}},
    'braketest':  {'enabled': True,  'frame':         {'anchor': 'sw', 'relx': 0.00,  'rely': 1.00}},
    'launchtest': {'enabled': True,  'frame':         {'anchor': 'sw', 'relx': 0.20,  'rely': 1.00}},
    'gearstats':  {'enabled': True,  'frame':         {'anchor': 'se', 'relx': 0.65,  'rely': 1.00}} } }
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
- draw map of circuit with left/right side?
- move torque graph to a frame inside the window?
  https://splunktool.com/resizing-a-matplotlib-plot-in-a-tkinter-toplevel
-make use of styles to remove constant references to bg/fg colors
-attempt to use styles, seems non-trivial and requires more ttk usage
-remove forza dependency
-figure out if socket can be closed cleanly

NOTES
fdp.dist_traveled seems broken for freeroam
reverse gear is not a fixed ratio. maybe fixed per transmission?


'''

class GUIDummy():
    """Dummy GUI plugin class
    If new plugins are added with extra variables or functions that are called, add them here
    If functions return values, the GUI will probably still crash. Oh well.
    """
    NAMES = set(['display', 'update', 'set_canvas', 'reset'])
    NAMES.update(['toggle_gatherratios', 'get_gearratios', 'set_gearratios', 'set_shiftrpms']) #guigearstats
    NAMES.update(['update_leds', 'set_rpmtable']) #guiled
    NAMES.update(['set_trace']) #guicarinfo
    NAMES.update(['set_wheelsizes', 'get_wheelsizes', 'set_tracking']) #guiwheelsize
    
    def __init__(self, *args, **kwargs):        
        def doNothing(*args, **kwargs):
            pass
        
        for func in self.NAMES:
            setattr(self, func, doNothing)

class MainWindow:
    PLUGINS = {'carinfo':GUICarInfo, 'basic':GUIBasic, 'braketest':GUIBraketest, 
               'gearstats':GUIGearStats, 'laptimes':GUILaptimes, 'lateralg':GUILateralG,
               'launchtest':GUILaunchtest, 'ledbar':GUILed, 'map':GUIMap, 
               'suspension':GUISuspension, 'wheelsize':GUIWheelsize}
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
        for name, GUIPlugin in self.PLUGINS.items():
            setattr(self, name, GUIPlugin(self.logger, self.root) if enabled[name] else GUIDummy())
        
        #helper array for loops
        self.plugins = [getattr(self, name) for name in self.PLUGINS]

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
        self.root.grid_rowconfigure(0, minsize=700, weight=700)
        self.root.grid_rowconfigure(1, minsize=325, weight=325)

        # Configure the cols that are in use to have weight #
        self.root.grid_columnconfigure(0, minsize=265, weight=265)
        self.root.grid_columnconfigure(1, minsize=675, weight=675)
        self.root.grid_columnconfigure(2, minsize=150, weight=150)

        self.root.title("ForzaGUI")
        self.root.geometry(f"1050x950+{config['window_offset_x']}+{config['window_offset_y']}")
        self.root.minsize(1100, 1025)
        self.root.maxsize(1100, 1025)
        self.root["background"] = constants.background_color
    
    def __init__variables(self):           
        self.infovarlist = ('car_ordinal', 'car_class', 'car_performance_index',
                            'drivetrain_type', 'num_cylinders', 
                            'engine_max_rpm', 'engine_idle_rpm')
        
        # self.infovar_tree = {}
        self.infovar_car_ordinal = None
        self.infovar_car_performance_index = None
        
        self.prevrev_torque = 0
        self.revlimit = 0

        self.collect_rpm = 0    
        self.trace = None
        self.rpmtable = [0 for x in range(1,11)]      
        
        self.torquegraph_var = tkinter.IntVar(value=0)
        
        self.filelogging_var = tkinter.IntVar(value=0)
        self.file = None
        self.fileheaderwritten = False
    
    def update_car_info(self, fdp):
        """update car info

        Args:
            fdp: fdp
        """
        if fdp.gear == 11: #gear 11 is neutral, hit when triggering events in the map
            return         #this breaks various hardcoded array limits
        
        #wait for revs to increase
        if self.collect_rpm == 1 and fdp.accel > 0 and fdp.current_engine_rpm > self.prevrev_torque:
                self.collect_rpm = 2
                self.trace = Trace(gear_collected=fdp.gear,
                                   gears=self.gearstats.get_gearratios())
        #collect data
        if self.collect_rpm == 2:
            if fdp.power > 0 and fdp.accel > 0:
                self.trace.add(fdp)
            else: #finish up and draw graph
                self.logger.info("Draw graph by pressing the Sweep (F8) button")
                self.trace.finish()
                self.add_carinfo_to_trace(fdp)
                self.trace.writetofile(f"traces/trace_ord{fdp.car_ordinal}_pi{fdp.car_performance_index}.json")
                self.collect_rpm = 0
                self.revlimit = self.trace.rpm[-1] #fdp.current_engine_rpm
        self.prevrev_torque = fdp.current_engine_rpm
        
        if fdp.car_ordinal != 0 and self.infovar_car_ordinal != fdp.car_ordinal:
            self.reset_car_info()
            self.infovar_car_ordinal = fdp.car_ordinal
            self.infovar_car_performance_index = fdp.car_performance_index
            # self.update_car_info_infovars(fdp)
            self.torquegraph_var.set(0)
            self.load_data(None)
        
        for plugin in self.plugins:
            plugin.update(fdp)
        
        if self.file is not None and fdp.is_race_on == 1:
            if not self.fileheaderwritten:
                self.file.write(fdp.get_tsv_header() + '\n')
                self.fileheaderwritten = True
            self.file.write(fdp.to_tsv() + '\n')
        
        #update display variables
        self.display_car_info()

    def add_carinfo_to_trace(self, fdp):
        carinfo = {}
        carinfo = dict(zip(self.infovarlist, fdp.to_list(self.infovarlist)))
        carinfo['drivetrain_type'] = ['FWD', 'RWD', 'AWD'][carinfo['drivetrain_type']]
        if config['plugins']['wheelsize']['enabled']:
            carinfo.update(self.wheelsize.get_wheelsizes())
        carinfo['shiftdelay'] = self.gearstats.shiftdelay_median
        self.trace.add_to_carinfo(carinfo)
                    
    def load_data(self, event):
        #self.logger.info("Load data button was pressed!")
        filename = f"traces/trace_ord{self.infovar_car_ordinal}_pi{self.infovar_car_performance_index}.json"
        if os.path.exists(filename):
            self.trace = Trace(fromfile=True, filename=filename)
            self.logger.info(f"loaded file {filename}")
            self.trace.finish()
            self.revlimit = self.trace.rpm[-1] #TODO: phase out
            self.gearstats.set_gearratios(self.trace.gears)
            self.rpmtorque_handler(None)
            self.wheelsize.set_wheelsizes(self.trace.carinfo)
            self.carinfo.set_trace(self.trace)
        else:
            self.wheelsize.set_tracking(True)
            self.logger.info("File does not exist")

    def display_car_info(self):
        self.suspension.display()
        self.wheelsize.display()
        self.laptimes.display()
        #self.carinfo.display()
        self.lateralg.display()
        self.gearstats.display()

    def reset_car_info(self):
        """reset car info and tree view
        """
        self.infovar_car_ordinal = None
        self.infovar_car_performance_index = None

        for plugin in self.plugins:
            plugin.reset()

        self.prevrev_torque = 0
        self.revlimit = 0
        
        self.car_ordinal = 0
        self.car_performance_index = 0
      
        self.collect_rpm = 0
        self.trace = None
        
        self.rpmtable = [0 for x in range(11)]
        
        if self.file is not None:
            self.file.close()
        self.filelogging_var.set(0)
        self.fileheaderwritten = False
    
    def set_car_info_frame(self):
        """set car info frame
        """
        pass
     
        #arguably unnecessary? 
        # load_data_button = tkinter.Button(self.car_info_frame, text='Load torque/ratios', bg=constants.background_color, fg=constants.text_color,
        #                         borderwidth=3, highlightcolor=constants.text_color, highlightthickness=True)
        # load_data_button.bind('<Button-1>', self.load_data)
        # load_data_button.pack()

        # self.car_info_frame.grid(row=0, column=0, sticky='news')

    def filelogging_toggled(self):
        if self.filelogging_var.get() == 1:
            writemode = 'a' if self.fileheaderwritten else 'w'
            try:
                self.file = open('log/fdp.tsv', writemode)
            except:
                self.logger.info("Cannot open log/fdp.tsv")
        else:
            self.file.close()

    def set_car_perf_frame(self):
        """set car perf frame
        """
        # Place car perf frame
        self.car_perf_frame = tkinter.Frame(self.root, border=0, bg=constants.background_color, relief="groove",
                                            highlightthickness=True, highlightcolor=constants.text_color)
        self.car_perf_frame.grid(row=0, column=0, sticky='news', columnspan=3)

        canvas_plugins = self.plugins #currently no plugins outside of car_perf_frame
        
        for p in canvas_plugins:
            p.set_canvas(self.car_perf_frame)
            
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
        self.button_frame = tkinter.Frame(self.root, border=0, relief="groove", bg=constants.background_color,
                                          highlightthickness=True, highlightcolor=constants.text_color)

        tkinter.Checkbutton(self.button_frame, text='File logging', variable=self.filelogging_var, 
                            bg=constants.background_color, fg=constants.text_color, command=self.filelogging_toggled,
                            onvalue=1, offvalue=0).pack()
        
        tkinter.Checkbutton(self.button_frame, text='Draw torque graph', variable=self.torquegraph_var, 
                            bg=constants.background_color, fg=constants.text_color,
                            onvalue=1, offvalue=0).pack()
        
        extra_button_frame = tkinter.Frame(self.button_frame, bg=constants.background_color)
        button_names = [('Connect', self.collect_data_handler, constants.collect_data),
                        ('Collect ratios', self.gatherratios_handler, constants.gatherratios),
                        ('Sweep', self.rpmtorque_handler, constants.analysis),
                        ('Reset', self.reset_handler, constants.reset)]
        
        for i, (name, func, shortcut) in enumerate(button_names):
            button = tkinter.Button(extra_button_frame, text=f'{name} ({shortcut.name})',
                                    bg=constants.background_color, fg=constants.text_color, borderwidth=3,
                                    highlightcolor=constants.text_color, highlightthickness=True)
            button.bind('<Button-1>', func)
            button.place(relx=0.5, rely=1 / len(button_names) * i + 1 / len(button_names) / 2, relwidth=0.8,
                         relheight=1 / len(button_names) * 0.9, anchor='center')

        extra_button_frame.pack(fill='both', expand=True)
        self.button_frame.grid(row=1, column=2, sticky='news')

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
        self.log_frame.grid(row=1, column=0, sticky='news', columnspan=2)

    def set_program_info_frame(self):
        """set code info frame
        """
        pass
        # self.program_info_frame = tkinter.Frame(self.root, border=0, bg=constants.background_color,
        #                                         relief="groove",
        #                                         highlightthickness=True, highlightcolor=constants.text_color)
        # # self.gearstats.set_canvas(self.program_info_frame)
        # self.program_info_frame.grid(row=1, column=0, sticky='news')

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

    def calculate_shiftrpms(self):
        rpm = self.trace.rpm
   #     torque = self.trace.torque
        power = self.trace.power #power in kw
     #   speed = self.trace.speed #speed in kmh
                    
        gears = [ratio for ratio in self.gearstats.get_gearratios() if ratio != 0]
        ratios = [gears[x]/gears[x+1] for x in range(len(gears)-1)]
        
        self.logger.info([round(g, 3) for g in gears])
        self.logger.info([round(r, 3) for r in ratios])
        
        X = 0
        shiftrpms_new = [intersect.intersection(rpm, power, rpm*ratio, power)[X] for ratio in ratios]
        shiftrpms_new = [i[X] if len(i) > 0 else rpm[-1] for i in shiftrpms_new]
        for i, (shiftrpm, ratio) in enumerate(zip(shiftrpms_new, ratios)):
            self.rpmtable[i+1] = int(round(shiftrpm, 0))
            self.logger.info(f"{i+1}: shift rpm {self.rpmtable[i+1]}, drop to {int(shiftrpm/ratio)}, "
                  f"drop is {int(shiftrpm*(1.0 - 1.0/ratio))}")
        
        self.ledbar.set_rpmtable(self.rpmtable, self.revlimit, self.trace)
        self.gearstats.set_shiftrpms(self.rpmtable)

    def plot_shiftrpms(self):
        rpm = self.trace.rpm
        torque = self.trace.torque
   #     power = self.trace.power #power in kw
        speed = self.trace.speed #speed in kmh
        
        gears = [ratio for ratio in self.gearstats.get_gearratios() if ratio != 0]
     #   ratios = [gears[x]/gears[x+1] for x in range(len(gears)-1)]

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
                label = f'{i+1:>2}  maxspeed {rpm[-1]/val:5.0f}'
            else:
                label = f'{i+1:>2} {s:>9} {gears[-1]*s/(val*g):>10.0f}'
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

    def rpmtorque_handler(self, _):
        #log data (through update_car_info) if no data exists
        if self.trace is None:
            self.collect_rpm = 1
            self.logger.info("Logging rpm/torque/power")
            return
        
        self.collect_rpm = 0
        self.logger.info("Doing maths")
        
        self.calculate_shiftrpms()
        
        if self.torquegraph_var.get():
            self.plot_shiftrpms()

    def gatherratios_handler(self, _):
        self.gearstats.toggle_gatherratios()

    def reset_handler(self, event):
        """ run reset callback
        
        Args:
            event
        """
        self.reset_car_info()

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
        elif key == constants.reset:
            self.reset_handler(None)
        elif key == constants.gatherratios:
            self.gatherratios_handler(None)

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
    threadPool.shutdown(wait=False)
    forza.server_socket.close()
    listener.stop()

def main():
    """main.....
    """
    MainWindow()

if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""
Created on Fri Oct 28 18:48:33 2022

@author: RTB
"""

import os
import tkinter
import tkinter.ttk
import math
import statistics
import intersect
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.widgets import Slider, RangeSlider, Button, CheckButtons
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
from dragderivation import Trace, DragDerivation
from cardata import CarData

import ctypes
PROCESS_PER_MONITOR_DPI_AWARE = 2
ctypes.windll.shcore.SetProcessDpiAwareness(PROCESS_PER_MONITOR_DPI_AWARE)

'''
TODO:
    - add awd slider for center diff (current assumption is 60%)
    - override slider to add ability to enter ratio
    - add information on shifts
    - add duration for gear at full throttle and no traction issues
    - investigate torque output during a shift
    - maybe replace matplotlib slider with tkinter slider
    - add dump to excel file for all variables
    - rewrite to use pyqtgraph and qt due to limitations in tkinter/matplotlib
    - consider https://matplotlib.org/stable/api/scale_api.html#matplotlib.scale.FuncScale

moving the matplotlib sliders into their own canvas resulted in the main canvas
not updating. May be due to a lack of an update call:
        self.canvas.draw() seems to be far slower than fig.canvas.draw_idle()
        self.canvas.draw() #should be called every update, doesn't seem to be required at all?
'''


    
def main ():
    Window()

# suppress matplotlib warning while running in thread
import warnings
warnings.filterwarnings("ignore", category=UserWarning)

#unused lowpass filter code
# from scipy.signal import butter, lfilter#, freqz
# def butter_lowpass(cutoff, fs, order=5):
#     return butter(order, cutoff, fs=fs, btype='low', analog=False)

# def butter_lowpass_filter(data, cutoff, fs, order=5):
#     b, a = butter_lowpass(cutoff, fs, order=order)
#     y = lfilter(b, a, data)
#     return y

# #accel_filtered = butter_lowpass_filter(accel, cutoff, fs, order)

# # Filter requirements.
# order = 6  #higher is steeper, see https://stackoverflow.com/questions/63320705/what-are-order-and-critical-frequency-when-creating-a-low-pass-filter-using
# fs = 60.0       # sample rate, Hz
# cutoff = 5.00  # desired cutoff frequency of the filter, Hz

DISPLAY_ALL = True

class Window ():
    width = 1550
    height = 1030

    graph_height = 850
    graph_width = 1000
    
    slider_height = 500
    slider_width = 550
    
    frameinfo_height = 400

    #maxlen model 46, maxlen maker 24, maxlen group 21 : 2023-04-32
    # _ in lambda because it is called as a class function and has self or cls in front, sadly
    NAMESTRING = lambda _, data: "{maker} {model} ({year}) {group} PI:{car_performance_index} o{car_ordinal}".format(**data)
    
    DEFAULTCARDATA = {'maker':'Acura', 'model':'NSX', 'year':2017, 'car_performance_index':831, 'group':'MODERN SUPERCARS', 'car_ordinal':2352}
    DEFAULTCAR =  NAMESTRING(None, DEFAULTCARDATA) #'Acura NSX (2017) PI:831 MODERN SUPERCARS o2352'
    TRACE_DIR = 'traces/'

    def __init__(self):
        self.root = tkinter.Tk()
        self.root.tk.call('tk', 'scaling', 1.5) #Spyder console fix for DPI too low
        self.root.title("Interactive gearing for collected traces for ForzaGUI")
        self.root.geometry(f"{self.width}x{self.height}")
        self.root.minsize(self.width, self.height)

        self.generate_carlist()

        self.combobox = tkinter.ttk.Combobox(self.root, width=100,
                                             exportselection=False, state='readonly',
                                             values=sorted(self.carlist.keys()))
        index = sorted(self.carlist.keys()).index(Window.DEFAULTCAR)
        self.combobox.current(index)
        self.combobox.bind('<<ComboboxSelected>>', self.carname_changed)
        
        self.filter_var = tkinter.IntVar(value=1)
        self.filter_button = tkinter.Checkbutton(self.root, text='Filter old traces', 
                                                 variable=self.filter_var, command=self.filter_toggle,
                                                 onvalue=1, offvalue=0)
        
        self.frame = tkinter.Frame(self.root)
        px = 1/plt.rcParams['figure.dpi'] # pixel in inches
        self.fig = Figure(figsize=(self.graph_width*px, self.graph_height*px), dpi=100)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.frame)
        self.fig_slider = Figure(figsize=(self.slider_width*px, self.slider_height*px), dpi=100)
        self.canvas_slider = FigureCanvasTkAgg(self.fig_slider, master=self.frame)
        
        self.frame.grid_rowconfigure(0, minsize=self.slider_height, weight=self.slider_height)
        self.frame.grid_rowconfigure(1, minsize=self.frameinfo_height, weight=self.frameinfo_height)
        self.frame.grid_columnconfigure(0, minsize=self.slider_width, weight=self.slider_width)
        self.frame.grid_columnconfigure(1, minsize=self.graph_width, weight=self.graph_width)
        
        self.toolbar = NavigationToolbar2Tk(self.canvas, self.root, pack_toolbar=False)
        self.toolbar.update()

        self.notebook = tkinter.ttk.Notebook(self.frame)
        self.frame_info = tkinter.Frame(self.frame)
        self.info = InfoFrame()
        self.info.set_canvas(self.frame_info)       
        self.power_graph = PowerGraph(self.notebook)
        self.torque_deriv_graph = TorqueDerivative(self.notebook)
        self.notebook.add(self.frame_info, text="Statistics")
        self.notebook.add(self.power_graph.frame, text='Power')
        self.notebook.add(self.torque_deriv_graph.frame, text='Torque\'')

        self.carname_changed() #force initial update to default car
                
        self.toolbar.pack(      side=tkinter.BOTTOM, fill='x')
        self.frame.pack(        side=tkinter.BOTTOM, fill='both', expand=True)
        self.filter_button.pack(side=tkinter.RIGHT)
        self.combobox.pack(     side=tkinter.RIGHT, expand=True)
        
        self.canvas_slider.get_tk_widget().grid(row=0, column=0)#, sticky=tkinter.NSEW)
        # self.frame_info.grid(row=1, column=0, sticky=tkinter.NW)
        self.notebook.grid(row=1, column=0, sticky=tkinter.NSEW)
        self.canvas.get_tk_widget().grid(row=0, column=1, rowspan=2)#, sticky=tkinter.NSEW)
        
        self.root.mainloop()
    
    def filter_toggle(self):
        if self.filter_var.get():
            self.combobox['values'] = sorted(self.carlist.keys())
        else:
            self.combobox['values'] = sorted(self.carlist_all.keys())
    
    def entry_validation(input, varname, maxval):
        print(f'validating {input}')
        if float(input) < 0 or len(input) > len(maxval):
            return False
        return True

    def carname_changed(self, event=None):
        carname = self.combobox.get()
        filename = self.carlist_all[carname]
        trace = Trace(fromfile=True, filename=filename)

        #reduce point count to roughly 125-150 for performance reasons
        decimator = int(len(trace.array) / 125)
        last = trace.array[-1]
        start = trace.array[:Trace.REMOVE_FROM_START]
        trace.array = start + trace.array[Trace.REMOVE_FROM_START:-1:decimator] + [last]
        trace.finish()

        final_ratio = Sliders.average_final_ratio(trace.gears)

        self.fig.clf()
        if self.fig_slider is not None:
            self.fig_slider.clf()
        self.gearing = Gearing(trace, self.fig, final_ratio=final_ratio, title=carname, fig_slider=self.fig_slider)
        
        self.drag = DragDerivation(trace=None, filename=filename)
        self.drag.draw_torquelosttodrag(ax=self.gearing.ax, step_kmh=Gearing.STEP_KMH, **self.drag.__dict__)
        
        self.info.carname_changed(carname, packet=None, trace=trace, drag=self.drag)
        self.frame_info.update() #required since adding Notebook layer
        self.power_graph.carname_changed(trace=trace)
        self.torque_deriv_graph.carname_changed(trace=self.drag)
        
        
    #filename structure:
    def generate_carlist(self):
        self.carlist = {}
        self.carlist_all = {}
        for entry in os.scandir(Window.TRACE_DIR):
            filename = entry.name
            ordinal = int(filename.split('_')[1][3:])
            pi = int(filename.split('_')[2][2:-5])

            data = CarData.getinfo(ordinal)
            if data is not None:
                data.update({'car_performance_index':pi})
                # carname = f"{data['maker']} {data['model']} ({data['year']}) PI:{pi} {data['group']} o{ordinal}"
                carname = self.NAMESTRING(data)
                trace = Trace(fromfile=True, filename=Window.TRACE_DIR + filename)
                self.carlist_all[carname] = Window.TRACE_DIR + filename
                if len(trace.data) > 0:
                    self.carlist[carname] = Window.TRACE_DIR + filename
            else:
                print(f'ordinal {ordinal} NOT FOUND')
        print(f'filtered car list contains {len(self.carlist)} items')
        print(f'total car list contains {len(self.carlist_all)} items')

#TODO: add a tab with a power graph
class PowerGraph():
    def __init__(self, frame):
        self.frame = tkinter.Frame(frame)
        self.fig = Figure(figsize=(546/100.0, 328/100.0), dpi=100)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.frame)
        self.canvas.get_tk_widget().pack(fill='both')#, expand=True)

    def carname_changed(self, trace):
        self.fig.clf()
        ax = self.fig.subplots(1)
        ax.plot(trace.rpm, trace.power)
        ax.grid()
        self.kw = self.fig.text(0.00, 0.00, "kW / RPM")
        for item in ([ax.title, ax.xaxis.label, ax.yaxis.label] +
             ax.get_xticklabels() + ax.get_yticklabels()):
            item.set_fontsize(8)
        self.fig.tight_layout()
        self.canvas.draw_idle()
    
class TorqueDerivative():
    DERIVE = False
    def __init__(self, frame):
        self.frame = tkinter.Frame(frame)
        self.fig = Figure(figsize=(546/100.0, 328/100.0), dpi=100)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.frame)
        self.canvas.get_tk_widget().pack(fill='both')#, expand=True)

    def carname_changed(self, trace):
        self.fig.clf()
        ax = self.fig.subplots(1)
        rpm, torque, power = trace.rpm, trace.torque, trace.power #zip(*sorted(zip(trace.rpm, trace.torque, trace.power)))
        rpm = np.array(rpm)
        torque = np.array(torque)
        power = np.array(power)
       # time = np.linspace(0, (len(trace.torque)-1)/60, len(trace.torque))
        torque_deriv = np.gradient(torque, rpm)
        i = np.argmax(power)
        torque_deriv_sorted = sorted(torque_deriv[i:])
        percentile = lambda array, pct: array[int(pct/100*len(array))]
        ymin = percentile(torque_deriv_sorted, 5)
        ymax = percentile(torque_deriv_sorted, 95)
        
        torque_deriv_filtered = [t for t in torque_deriv[i:] if t > ymin and t < ymax]
        ax.plot(torque_deriv_filtered)
        ax.grid()
        ax.set_ylim(ymin, ymax)
        self.kw = self.fig.text(0.00, 0.008, "Nm' / points  5/95% filtered derivative of torque past peak power")
        for item in ([ax.title, ax.xaxis.label, ax.yaxis.label] +
             ax.get_xticklabels() + ax.get_yticklabels()):
            item.set_fontsize(8)
        self.fig.tight_layout()
        self.canvas.draw_idle()

class InfoFrame():
    DEFAULT_CENTERDIFF = 70
    NAMESTRING = lambda _, data: "{maker} {model} ({year}) {group} PI:{car_performance_index} o{car_ordinal}".format(**data)
    CARNAME_FONTSIZE = 8
    
    def __init__(self, *args, **kwargs):        
        self.carname_var = tkinter.StringVar(value='')
        
        #if drag exists, trace does too
        #drag can be made from trace if None
        #packet is made from trace v2 if None
        
        #from carname, but easier with packet or trace v2
        self.weight_var = tkinter.IntVar(value=0)
        
        #packet required or trace v1:
        self.num_cylinders_var = tkinter.IntVar(value=0)
        self.engine_idle_rpm_var = tkinter.IntVar(value=0)
        self.engine_max_rpm_var = tkinter.IntVar(value=0)
        
        #trace v0 required but prefer drag (interactivetransmission decimates trace length)
        self.revlimit_var = tkinter.DoubleVar(value=0.0)
        self.peak_power_var = tkinter.DoubleVar(value=0)
        self.peak_power_rpm_var = tkinter.IntVar(value=0)
        self.peak_torque_var = tkinter.DoubleVar(value=0)
        self.peak_torque_rpm_var = tkinter.IntVar(value=0)
        self.top_speed_var = tkinter.DoubleVar(value=0.0)
        self.true_top_speed_var = tkinter.DoubleVar(value=0.0)
        self.true_top_speed_ratio_var = tkinter.StringVar(value=0.0)
        
        #trace v1 required:
        self.wheelsize_front_var = tkinter.DoubleVar(value=0.0)
        self.wheelsize_rear_var = tkinter.DoubleVar(value=0.0)
        self.shiftdelay_var = tkinter.DoubleVar(value=0.0)
        self.drivetrain_var = tkinter.StringVar(value='N/A')
        self.center_diff_var = tkinter.DoubleVar(value=50)
            
        #trace data required:
        self.peak_boost_var = tkinter.DoubleVar(value=0.0)
        self.drag_var = tkinter.DoubleVar(value=0.0)
        self.max_slipratio_front_var = tkinter.StringVar(value='')
        self.max_slipratio_rear_var = tkinter.StringVar(value='')
        self.torque_limit_var = tkinter.IntVar(value=0)
        self.transmission_efficiency_var = tkinter.DoubleVar(value=0.0)
        
    def set_canvas(self, frame, opts={}):
        frame.columnconfigure(5, weight=1000)
        table = [self.carname_var, 
                 ['Peak power:', self.peak_power_var, 'kW @', self.peak_power_rpm_var, 'rpm'], 
                 ['Peak torque:', self.peak_torque_var, 'Nm @', self.peak_torque_rpm_var, 'rpm'],
                 ['Peak boost:', self.peak_boost_var, 'bar'],
                 ['Revlimit:', self.revlimit_var, ''],
                 ['Engine:', self.engine_idle_rpm_var, 'rpm idle,', self.engine_max_rpm_var, 'rpm max'],
                 ['Num cylinders:', self.num_cylinders_var, ''], 
                 ['Top speed:', self.top_speed_var, 'km/h'],
                 ['vmax:', self.true_top_speed_var, 'km/h @', self.true_top_speed_ratio_var, 'ratio'],
                 ['Drag value:', self.drag_var, ' (100*C*wheelsize*efficiency)'],
                 ['Drivetrain:', self.drivetrain_var, ''],
                 ['Drivetrain loss:', self.transmission_efficiency_var, '%'],
                 ['Wheel radius:', self.wheelsize_front_var, 'front,', self.wheelsize_rear_var, 'rear (cm)'],
                 # ['Shift duration:', self.shiftdelay_var, 'seconds'],
                 ['Stock weight:', self.weight_var, 'kg'],
                 # ['Center diff:', self.center_diff_var, '% to rear if AWD'],
                 # ['Max slip ratio:', self.max_slipratio_front_var, '% front, ', self.max_slipratio_rear_var, '% rear']
                 # ['Torque limit:', self.torque_limit_var, 'Nm']
            ]
        
    #    entry_centerdiff_validation = self.root.register(Window.entry_centerdiff_validation)
        self.entries = {}
        carname_opts = opts.copy()
        carname_opts['font'] = tkinter.font.Font(size=self.CARNAME_FONTSIZE)
        tkinter.Label(frame, textvariable=table[0], **carname_opts).grid(row=0, column=0, columnspan=6)
        for i, row in enumerate(table[1:], start=1):
            tkinter.Label(frame, text=row[0], **opts).grid(row=i, column=0, sticky=tkinter.E)
            if row[0] == 'Weight:' or row[0] == 'Center diff:':
                self.entries[row[0]] = tkinter.Entry(frame, textvariable=row[1], width=5, state=tkinter.DISABLED, **opts)
                                                  #   validate='all', validatecommand=(entry_centerdiff_validation, '%P'))
                self.entries[row[0]].grid(row=i, column=1)
            else:
                tkinter.Label(frame, textvariable=row[1], **opts).grid(row=i, column=1)
                
            if len(row) == 3:
                tkinter.Label(frame, text=row[2], **opts).grid(row=i, column=2, columnspan=3, sticky=tkinter.W)
            else:
                tkinter.Label(frame, text=row[2], **opts).grid(row=i, column=2, sticky=tkinter.W)
                tkinter.Label(frame, textvariable=row[3], **opts).grid(row=i, column=3)
                tkinter.Label(frame, text=row[4], **opts).grid(row=i, column=4, sticky=tkinter.W)

     #  self.revlimit_var.set(int(25*round(drag.rpm[-1]/25, 0))) #round to nearest 25 #maybe use elsewhere?
    def carname_changed(self, carname=None, packet=None, trace=None, drag=None):
        self.reset_vars()
                
        trace_v1plus = (trace is not None and trace.version >= 1)
        trace_v2 = (trace is not None and trace.version == 2)
                
        if drag is None and trace is not None:
            drag = DragDerivation(trace=trace)#, filename=self.carlist[carname]) #we don't know if trace is untouched
        if trace_v2:
            data = trace.data_to_fdp()
            packet = data[0] if packet is None else packet

        ordinal = None
        if carname:
            ordinal = int(carname.split(' ')[-1][1:]) #ugly
            pi = int(carname.split(' ')[-2][3:])
        elif packet:
            ordinal = packet.car_ordinal
            pi = packet.car_performance_index
            
        if ordinal:
            cardata = CarData.getinfo(ordinal)
            if cardata is None:
                carname = f'Unknown car ord:{ordinal} pi:{pi}'
            else:
                cardata.update({'car_performance_index': pi})
                carname = self.NAMESTRING(cardata)
                self.weight_var.set(cardata['weight'])
            self.carname_var.set(carname)
        
        if packet is not None: #or trace_v2            
            self.num_cylinders_var.set(packet.num_cylinders)
            self.engine_idle_rpm_var.set(int(round(packet.engine_idle_rpm, 0)))
            self.engine_max_rpm_var.set(int(round(packet.engine_max_rpm, 0))) 
            self.drivetrain_var.set(['FWD', 'RWD', 'AWD'][packet.drivetrain_type])
        
        if trace is not None: #trace_v0plus
            source = drag if drag is not None else trace
            peak_power_index = np.argmax(source.power)
            self.peak_power_var.set(round(max(source.power), 1))
            self.peak_power_rpm_var.set(int(source.rpm[peak_power_index]))
            peak_torque_index = np.argmax(source.torque)
            self.peak_torque_var.set(round(max(source.torque), 1))
            self.peak_torque_rpm_var.set(int(source.rpm[peak_torque_index]))
            self.revlimit_var.set(math.ceil(source.rpm[-1]))
            self.top_speed_var.set(round(drag.top_speed_by_drag(**drag.__dict__), 1))
            gear_ratio, top_speed = drag.optimal_final_gear_ratio(**drag.__dict__)
            self.true_top_speed_var.set(round(top_speed, 1))
            self.true_top_speed_ratio_var.set(round(gear_ratio, 3))
        
        if packet is None and trace_v1plus:
            self.drivetrain_var.set(trace.carinfo.get('drivetrain_type', 'N/A'))
        
        if trace_v1plus:
            wheelsize_front = float(trace.carinfo.get('wheelsize_front', 0))
            wheelsize_rear = float(trace.carinfo.get('wheelsize_rear', 0))        
            self.wheelsize_front_var.set(f'{wheelsize_front:.2f}')
            self.wheelsize_rear_var.set(f'{wheelsize_rear:.2f}')
        
            wheelsize = 'N/A'
            if self.drivetrain_var.get() == 'FWD':
                wheelsize = wheelsize_front
                self.center_diff_var.set(0)
                # self.centerdiffentryenabled(False)
            elif self.drivetrain_var.get() == 'RWD':
                wheelsize = wheelsize_rear
                self.center_diff_var.set(100)
                # self.centerdiffentryenabled(False)
            elif self.drivetrain_var.get() == 'AWD':
                wheelsize = ((1-InfoFrame.DEFAULT_CENTERDIFF/100)*wheelsize_front 
                             + InfoFrame.DEFAULT_CENTERDIFF/100*wheelsize_rear)
                self.center_diff_var.set(InfoFrame.DEFAULT_CENTERDIFF)
                # self.centerdiffentryenabled(True)


            shift_delay = trace.carinfo.get('shiftdelay', 0)
            shift_delay = f"±{shift_delay/60:.3f}" if shift_delay != 0 else 'N/A'
            self.shiftdelay_var.set(shift_delay)

        if (trace_v1plus and packet) or trace_v2:
            efficiency = 1/statistics.median((drag.torque_adj - drag.C*drag.speed*drag.speed)/wheelsize/drag.accel/self.weight_var.get()) if wheelsize not in ['N/A', 0] else 0
            self.transmission_efficiency_var.set(f'{100 - efficiency:.1f}')
            self.drag_var.set(round(100* drag.C / wheelsize * efficiency, 1))

        if trace_v2:
            boost = [point.boost/14.504 for point in data]
            self.peak_boost_var.set(round(max(boost), 2))
            
            # print(carname)
            # self.derive_max_slipratio(data, wheelsize_front, wheelsize_rear)
            # self.derive_max_torque(data, self.drivetrain_var.get(), drag)

    #reset all object variables that end in _var
    def reset_vars(self):
        [var.set('N/A') for key, var in self.__dict__.items() if key[-4:] == '_var']
            
    #TODO: investigate
    def derive_max_torque(self, data, drivetrain_type, drag):
        if drivetrain_type == 'RWD':
            tires = ['RL', 'RR']
        elif drivetrain_type == 'FWD':
            tires = ['FL', 'FR']
        else: #AWD
            self.torque_limit_var.set("N/A")
            return
        ratio = drag.gearratio_collected
        
        max_torque = []
        for p in data:
            wheel_force = p.torque*ratio/2
            max_torque.extend([wheel_force/getattr(p, f'tire_slip_ratio_{tire}') for tire in tires])
        torque_limit = statistics.median(sorted(max_torque)[int(len(max_torque)/20):int(len(max_torque)/10)])
        print(sorted(max_torque)[int(len(max_torque)/20):int(len(max_torque)/10)])
        self.torque_limit_var.set(int(torque_limit))

    #TODO: investigate
    def derive_max_slipratio(self, data, wheelsize_front, wheelsize_rear, drawgraph=False):
        wheelsize = {'FL': wheelsize_front/100, 'FR': wheelsize_front/100,
                     'RL': wheelsize_rear/100, 'RR': wheelsize_rear/100}
        tiredata = {}
        if drawgraph:
            fig, ax = plt.subplots()
        count = len(data)
        ymin, ymax = 1, 0
        for tire in ['FL', 'FR', 'RL', 'RR']:
            val = [(wheelsize[tire] / (p.speed / getattr(p, f'wheel_rotation_speed_{tire}')) - 1) / getattr(p, f'tire_slip_ratio_{tire}') for p in data]
            #val = butter_lowpass_filter(val, cutoff, fs, order)  
            tiredata[tire] = statistics.median(val)
            if drawgraph:
                ax.plot([p.speed for p in data], val, label=tire)   
            #ax.plot(sorted(val), label=tire)
            val = sorted(val)
            fifthpct = val[int(count/20)]
            ninetyfifthpct = val[int(19*count/20)]
            ymin = min(fifthpct, ymin)
            ymax = max(ninetyfifthpct, ymax)
            print(f'{tire} 5th pct {fifthpct:.3f} median {tiredata[tire]:.3f} 95th pct {ninetyfifthpct:.3f}')
        
        if drawgraph:
            ax.legend()
            ax.set_ylim(ymin-0.01, ymax+0.01)
            plt.show()
        
        self.max_slipratio_front_var.set(f'{100*(tiredata["FL"]+tiredata["FR"])/2:.1f}')
        self.max_slipratio_rear_var.set(f'{100*(tiredata["RL"]+tiredata["RR"])/2:.1f}')
            
    
    # def centerdiffentryenabled(self, enable=True):
    #     enable = False #REMOVE AFTER IMPLEMENTING DYNAMIC CENTER DIFF
    #     state = tkinter.NORMAL if enable else tkinter.DISABLED
    #     self.entries['Center diff:'].config(state=state)



#helper class for class Gearing
class Gear():
    def __init__(self, gear, trace, ax, update_backref, final_ratio=1):
        self.gear, self.trace = gear, trace
        self.ratio = trace.gears[gear]
        self.final_ratio = final_ratio
        self.update_backref = update_backref
        self.rpmlimit = trace.rpm[-1]
        x,y = self.get_points()
        self.plot, = ax.plot(x, y, label=f'Gear {gear+1}')

    def get_points(self):
        full_ratio = self.ratio*self.final_ratio
        x = [x/full_ratio for x in self.trace.rpm if x <= self.rpmlimit]
        y = [x*full_ratio for x,y in zip(self.trace.torque, self.trace.rpm) if y <= self.rpmlimit]
        return (x,y)

    def add_slider(self, ax, slider):
        self.ax, self.slider = ax, slider

    def update_rpmlimit(self, value):
        self.rpmlimit = value
        self.redraw()

    def update(self, value):
        self.ratio = value
        self.redraw()
        self.update_backref(value)

    def update_final_ratio(self, value):
        self.final_ratio = value
        self.redraw()

    def redraw(self):
        x,y = self.get_points()
        self.plot.set_xdata(x)
        self.plot.set_ydata(y)

class Gearing ():
    STEP_KMH = 25
    
    def __init__(self, trace, fig=None, final_ratio=1, title=None, fig_slider=None,
                 car_ordinal=None, car_performance_index=None):
        if fig == None:
            self.fig, (self.ax, ax2) = plt.subplots(2,1, gridspec_kw={'height_ratios': [2,1]})
            self.fig.set_size_inches(16, 10)
        else:
            self.fig = fig
            self.ax, ax2 = self.fig.subplots(2,1, gridspec_kw={'height_ratios': [2,1]})

        self.__init__graph(trace, final_ratio, title, car_ordinal, car_performance_index)
        self.__init__power_contour()
        
        self.legend = self.ax.legend()  #force add legend to axis due to extra legend being added later
        self.ax.add_artist(self.legend) #see https://matplotlib.org/stable/tutorials/intermediate/legend_guide.html
        
        self.fig.tight_layout()
        
        separate_fig = True
        if fig_slider == None:
            fig_slider = self.fig
            separate_fig = False            
        self.sliders = Sliders(fig_slider, self.final_ratio, self.gears, 
                               self.trace, self.xmax, self.rpmperkmh, separate_fig)
        self.sliders.final_ratio_onchanged(self.update_final_ratio)
        self.sliders.rpmlimit_onchanged(self.update_rpmlimit)
        self.sliders.integral_onchanged(self.update_integral)
        
        self.shiftrpm = ShiftRPM(fig_slider, self.ax, self.gears, self.legend, self.fig.canvas.draw_idle)
        
        self.differencegraph = DifferenceGraph(ax2, self.gears, self.power_contour, 
                                               self.rpmperkmh, self.xmax, self.xticks)
        
        fig_text = fig_slider if fig_slider is not None else fig #TODO: move integral text to DifferenceGraph?
        self.integral_text = fig_text.text(*Sliders.axes['integral_text'], "Gearing efficiency: 100% in range")
        
        self.disclaimer = fig_text.text(*Sliders.axes['disclaimer'], 'Shift rpm values valid if and only if: \nFull throttle, shift duration is 0, no traction limit')
        
        self.print_integral()

    def __init__graph(self, trace, final_ratio, title, car_ordinal, car_performance_index):
        self.trace = trace
        self.final_ratio = final_ratio
        self.trace.gears = [g/final_ratio for g in self.trace.gears]

        self.gears = []
        for i, ratio in enumerate(self.trace.gears):
            self.gears.append(Gear(i, trace, self.ax, self.update, final_ratio))
        
        #sort rpm and torque to be monotonically increasing on rpm
        rpm, torque = zip(*sorted(zip(self.trace.rpm, self.trace.torque)))
        self.trace.rpm = np.array(rpm)
        self.trace.torque = np.array(torque)

        #1 km/h per x rpm, scaled to final ratio
        self.rpmperkmh = (statistics.median([(a/b) for (a, b) in zip(self.trace.rpm, self.trace.speed)]) /
               (self.trace.gears[self.trace.gear_collected-1]*self.final_ratio))
        valstep = Gearing.STEP_KMH*self.rpmperkmh

        #if the x values are converted to speed, we seem to lose accuracy in drawing the power contour
        #therefore, use rpm/ratio and hide the xtick true values
        self.xmax = math.ceil(self.trace.rpm[-1]/(self.gears[-1].ratio*self.final_ratio)*valstep)/valstep
        self.xticks = np.arange(0,self.xmax+valstep,valstep)

        ymax = max(self.trace.torque*self.gears[0].ratio*self.final_ratio)*1.01
        self.ax.set_ylim(0, ymax)
        self.ax.set_xlim(0, self.xmax)
        self.ax.set_xticks(self.xticks)
        self.ax.set_xlabel("speed (km/h)")
        self.ax.set_ylabel("torque (Nm)")
        self.ax.set_xticklabels([math.ceil(x/self.rpmperkmh) for x in self.xticks])
        
        self.ax.grid()
        
        #display coords in toolbar when cursor in gearing graph
        self.ax.format_coord = lambda x,y: f'Speed:{x/self.rpmperkmh:5.1f} km/h, Torque:{y:5.0f} Nm'

        if title is None:
            if car_ordinal is not None:
                data = CarData.getinfo(car_ordinal)
                title = f"{data['maker']} {data['model']} ({data['year']}) PI:{car_performance_index} {data['group']}"
            else:
                title = ''
                print("we missing a title")
        self.ax.set_title(title)  

    # def find_intersections(self):
    #     self.data = [graph.get_points() for graph in self.gears]
    #   #  data = [(x, y-self.power_contour(x)) for x,y in data]
    #     intersections = [intersect.intersection(x1, y1, x2, y2) for (x1,y1), (x2, y2) in zip(self.data[:-1], self.data[1:])]
    #     ratios = [graph.ratio*self.final_ratio for graph in self.gears]
    #     intersections = [x*r for (x,y),r in zip(intersections, ratios)]
    #     #print(intersections)
    #     return intersections

    def __init__power_contour(self):
        i = self.trace.power.argmax()
        peak_power_torque = self.trace.torque[i]
        peak_power_rpm = self.trace.rpm[i]

        self.power_contour = lambda rpm: peak_power_torque*peak_power_rpm/rpm
        rpmmax = int(2*self.trace.rpm[-1])
        self.ax.plot(self.power_contour(range(1, rpmmax)), label='Peak power torque')

    def update_integral(self, value):
        self.sliders.lower, self.sliders.upper = value
        self.print_integral()
    
    #TODO: investigate: integral answer is questionable
    def print_integral(self):
       x,y = self.differencegraph.get_difference()
       lower = self.sliders.lower*self.rpmperkmh
       upper = self.sliders.upper*self.rpmperkmh
       y = [b+self.power_contour(a) for a, b in zip(x, y) if a >= lower and a <= upper]
       x = [a for a in x if a >= lower and a <= upper]
       
       maximum = math.log(upper/lower)*self.power_contour(1)
       #print(x, y)
       integral = np.trapz(y, x)
       percentage = 100*integral/maximum
       self.integral_text.set_text(f"Gearing efficiency: {percentage:5.1f}% in range")
       self.fig.canvas.draw_idle()

    def update_rpmlimit(self, value):
        self.sliders.rpmlimit = value
        for graph in self.gears:
            graph.update_rpmlimit(value)
        self.redraw_difference()

    def update_final_ratio(self, value):
        self.sliders.final_ratio = value
        for graph in self.gears:
            graph.update_final_ratio(value)
        self.redraw_difference()

    def update(self, value):
        self.redraw_difference()
        for text, gear, next_gear in zip(self.sliders.rel_ratios_text, self.gears[:-1], self.gears[1:]):
            text.set_text(f'{gear.ratio/next_gear.ratio:.2f}')

    def redraw_difference(self):
        self.differencegraph.redraw_difference()
        self.shiftrpm.redraw()
        self.print_integral()
        #self.fig.canvas.draw_idle()
        
    def run(self):
        pass

class Sliders ():
    FINALRATIO_MIN = 2.2
    FINALRATIO_MAX = 6.1
    GEARRATIO_MIN = 0.48
    GEARRATIO_MAX = 6.00
    RATIO_STEP = 0.01
    xmin = 0.05
    xmax = 0.36

    axes = {'final_gear':            [0.05, 0.90,          0.2, 0.03],
            'gears':       lambda g: [0.05, 0.87-0.035*g,  0.2, 0.03],
            'rel_ratios':  lambda g: [0.27, 0.8625-0.035*g],
            'reset':                 [0.08, 0.51,          0.2, 0.03],
            'rpmlimit':              [0.05, 0.48,          0.2, 0.03],
            'integral':              [0.05, 0.45,          0.2, 0.03],
            'integral_text':         [0.06, 0.44],
            'checkbutton':           [0.01, 0.35, 0.10, 0.14],
            'disclaimer':            [0.01, 0.01]
            }

    #TODO: split __init__ up into sub functions
    def __init__(self, fig, final_ratio, gears, trace, xmax, rpmperkmh, separate_fig=False):
        if separate_fig:
         #   Sliders.xmin, Sliders.xmax = 0.2, 1.1
            Sliders.axes = {'final_gear':            [0.17, 0.95,           0.74, 0.025],
                            'gears':       lambda g: [0.17, 0.90-0.06*g,    0.74, 0.025],
                            'rel_ratios':  lambda g: [0.82, 0.87-0.06*g],
                            'reset':                 [0.7, 0.27,            0.2, 0.08],
                            'rpmlimit':              [0.18, 0.22,           0.7, 0.025],
                            'integral':              [0.18, 0.16,           0.6, 0.025],
                            'integral_text':         [0.21, 0.13],
                            'checkbutton':           [0.21, 0.00, 0.2, 0.2],
                            'disclaimer':            [0.01, 0.01]
                            }
        else:
            # create space for sliders
            fig.subplots_adjust(left=self.xmax)

        self.__init__gearsliders(fig, final_ratio, gears, trace)

        # Create a `matplotlib.widgzets.Button` to reset the sliders to initial values.
        self.ax_reset = fig.add_axes(self.axes['reset']) #0.72
        self.button = Button(self.ax_reset, 'Reset', hovercolor='0.975')
        def reset(event):
            self.final_gear_slider.reset()
            self.rpmlimit_slider.reset()
            for graph in gears:
                graph.slider.reset()
        self.button.on_clicked(reset)
        
        #create slider to limit rpm/torque graph to the defined rpm limit 
        #(think redline limit for automatic transmission)
        self.rpmlimit_ax = fig.add_axes(self.axes['rpmlimit'])
        self.rpmlimit_slider = Slider(
            ax=self.rpmlimit_ax,
            label='RPM limit',
            valmin=trace.rpm[0],
            valmax=trace.rpm[-1],
            valinit=trace.rpm[-1],
         #   valstep = 50
        )
        
        #default to peak power in first and last gear
        i = trace.power.argmax()
        if len(gears) == 1:
            self.lower = 1
            self.upper = xmax/rpmperkmh
        else:
            self.lower = trace.rpm[i]/gears[0].ratio/final_ratio/rpmperkmh
            self.upper = trace.rpm[i]/gears[-1].ratio/final_ratio/rpmperkmh
        self.integral_ax = fig.add_axes(self.axes['integral'])
        self.integral_slider = RangeSlider(
            ax=self.integral_ax,
            label='Integral\nlimits',
            valmin=0,
            valmax=xmax/rpmperkmh,
            closedmin=False,
            closedmax=True,
            valinit=(self.lower, self.upper),
            valstep=1,
            valfmt = "%4.0f" #override default to avoid 1.001 as value
        )
    
    def __init__gearsliders(self, fig, final_ratio, gears, trace):
        final_slider_limit, gear_slider_limit = self.slider_limits(final_ratio)

        #sliders must have a reference to stay interactive
        self.final_gear_ax = fig.add_axes(self.axes['final_gear'])
        self.final_gear_slider = Slider(
            ax=self.final_gear_ax,
            label='Final gear',
            valmin=final_slider_limit['valmin'],
            closedmin=False,
            valmax=final_slider_limit['valmax'],
            valinit= final_ratio,
            valstep = self.RATIO_STEP,
            valfmt = "%4.2f" #override default to avoid 1.001 as value
        )

        for gear, ratio in zip(gears, trace.gears):
            ax = fig.add_axes(self.axes['gears'](gear.gear))
            slider = Slider(
                ax=ax,
                label=f'gear {gear.gear+1}',
                valmin=gear_slider_limit['valmin'],
                closedmin=False,
                closedmax=False,
                valmax=gear_slider_limit['valmax']+self.RATIO_STEP,
                valinit=ratio,
                valstep = self.RATIO_STEP
            )
            gear.add_slider(ax, slider) #for resetting
            gear.slider.on_changed(gear.update)

        self.rel_ratios_text = []
        for gear, next_gear in zip(gears[:-1], gears[1:]):
            text = fig.text(*self.axes['rel_ratios'](gear.gear), 
                                          f'{gear.ratio/next_gear.ratio:.3f}')
            self.rel_ratios_text.append(text)

        #connect sliders: the ratio per slider must be between previous and next gear's ratios
        prev_gear = None
        for a, next_gear in zip(gears, gears[1:]+[None]):
            a.slider.slidermax = prev_gear.slider if prev_gear is not None else None
            a.slider.slidermin = next_gear.slider if next_gear is not None else None
            prev_gear = a
    
    def final_ratio_onchanged(self, func):
        self.final_gear_slider.on_changed(func)    
        
    def rpmlimit_onchanged(self, func):
        self.rpmlimit_slider.on_changed(func)
    
    def integral_onchanged(self, func):
        self.integral_slider.on_changed(func)

    @classmethod
    def slider_limits(cls, final_ratio):
        if final_ratio == 1:
            final_slider_settings = {'valmin': cls.FINALRATIO_MIN / cls.FINALRATIO_MAX,
                                     'valmax': cls.FINALRATIO_MAX / cls.FINALRATIO_MIN}
            gear_slider_settings = {'valmin': cls.FINALRATIO_MIN * cls.GEARRATIO_MIN,
                                    'valmax': cls.FINALRATIO_MAX * cls.GEARRATIO_MAX}
        else:
            final_slider_settings = {'valmin': cls.FINALRATIO_MIN,
                                     'valmax': cls.FINALRATIO_MAX}
            gear_slider_settings = {'valmin': cls.GEARRATIO_MIN,
                                    'valmax': cls.GEARRATIO_MAX}

        return (final_slider_settings, gear_slider_settings)
        
    @classmethod
    def average_final_ratio(cls, gears):
        upper_limit = min(gears[-1]/cls.GEARRATIO_MIN, cls.FINALRATIO_MAX) 
        lower_limit = max(gears[0]/cls.GEARRATIO_MAX, cls.FINALRATIO_MIN)
        return (upper_limit + lower_limit) / 2

class ShiftRPM ():
    DEFAULTSTATE = True
    
    def __init__(self, fig, ax_graph, gears, legend, draw_func=None):
        self.fig = fig
        self.ax_graph = ax_graph
        self.gears = gears
        self.legend = legend
                
        self.ax = fig.add_axes(Sliders.axes['checkbutton']) 
        self.ax.axis('off') #remove black border around axis
        self.buttons = CheckButtons(self.ax, ["Display shift RPM lines"], actives=[ShiftRPM.DEFAULTSTATE])
        self.buttons.on_clicked(self.set_visibility)
        
        _, self.ymax = self.ax_graph.get_ylim()
        intersections = self.get_intersections()
        self.vlines = [ax_graph.vlines(i, 0.0, self.ymax, linestyle=':') 
                                   for i, g in zip(intersections, self.gears)]
        
        self.draw_func = draw_func
        
        # for i, g in zip(intersections, self.gears):
        #     g.plot.set_label(f"Gear {g.gear+1}, shift at {i * g.final_ratio * g.ratio:5.0f} rpm")

        self.set_visibility(None)
        
    def set_visibility(self, _):
        toggle = all(self.buttons.get_status()) #assumes single checkbutton
        for vline in self.vlines:
            vline.set_visible(toggle)
        
        self.redraw()
        
        if self.draw_func is None:
            self.fig.canvas.draw_idle() #no longer works with sliders split to own canvas
        else:
            self.draw_func() #calls fig.canvas.draw_idle on graph canvas

    def redraw(self):
        intersections = self.get_intersections()      
        
        for i, g, t in zip(intersections, self.gears, self.legend.get_texts()):
            t.set_text(f"Gear {g.gear+1}, shift at {i * g.final_ratio * g.ratio:5.0f} rpm")

        if not all(self.buttons.get_status()):#assumes single checkbutton
            return

        for x, vline in zip(intersections, self.vlines):
            vline.set_segments( [np.array([[x, 0.0],[x, self.ymax]])])
        
    def get_intersections(self):
        X = 0
        data = [graph.get_points() for graph in self.gears]
        intersections = [intersect.intersection(x1, y1, x2, y2)[X] for (x1,y1), (x2, y2) in zip(data[:-1], data[1:])]
        intersections = [i[0] if len(i) > 0 else x[-1] for i, (x,y) in zip(intersections, data)]
    #    intersections = [i*g.ratio*g.final_ratio for i,g in zip(intersections, self.gears)]
    #is there a bug in using i[0] here? it would mean the first intersection point instead of the last one
        
        return intersections

class DifferenceGraph():
    PERCENTAGELOST_MAX = -30
    PERCENTAGELOST_STEP = 5
    YTICKS = range(PERCENTAGELOST_MAX, 1, PERCENTAGELOST_STEP)
    
    def __init__(self, ax, gears, power_contour, rpmperkmh, xmax, xticks):
        self.ax = ax
        self.gears = gears
        self.power_contour = power_contour
        self.rpmperkmh = rpmperkmh
        
        self.fillplot = None
        self.redraw_difference()

        self.ax.xaxis.tick_top()
        self.ax.set_xlim(0, xmax)
        self.ax.set_xticks(xticks)
        self.ax.set_xticklabels([])
        
        self.ax.set_ylim(DifferenceGraph.PERCENTAGELOST_MAX, 0)
        self.ax.set_ylabel("% of torque lost vs torque at peak power")
        self.ax.set_yticks(DifferenceGraph.YTICKS)
        self.ax.set_yticklabels([f'{y}%' for y in DifferenceGraph.YTICKS])
        
        #display coords in toolbar when cursor in difference graph
        self.ax.format_coord = lambda x,y: f'Speed:{x/rpmperkmh:5.1f} km/h, Loss:{y:5.1f}%'
        
        self.ax.grid()

    def get_difference(self):
        X = 0
        data = [graph.get_points() for graph in self.gears]
        intersections = [intersect.intersection(x1, y1, x2, y2)[X] for (x1,y1), (x2, y2) in zip(data[:-1], data[1:])]
        intersections = [i[0] if len(i) > 0 else x[-1] for i, (x,y) in zip(intersections, data)]
        
        min_rpm = data[0][X][0] #initial rpm of first gear
        max_rpm = data[-1][X][-1] #final rpm of final gear
        intersections = [min_rpm] + intersections + [max_rpm]
        x_array, y_array = [], []
        for start, end, (x,y) in zip(intersections[:-1], intersections[1:], data):
            x_array.extend([rpm for rpm in x if rpm >= start and rpm <= end])
            y_array.extend([torque - self.power_contour(rpm)
                                for rpm, torque in zip(x,y) if rpm >= start and rpm <= end])
        return (x_array, y_array)

    def redraw_difference(self):
        x_array, y_array = self.get_difference()
        
        #convert to percentage of optimal
        y_array = [100*y/self.power_contour(x) for x,y in zip(x_array, y_array)]
        #y_array = sorted(y_array)

        if self.fillplot is not None:
            self.fillplot.remove()
        self.fillplot = self.ax.fill_between(x_array, y_array, color='b')
        #    self.diffplot.remove()
        #    self.diffplot, = self.ax2.plot(x_array, y_array, 'b')

if __name__ == "__main__":
    main()
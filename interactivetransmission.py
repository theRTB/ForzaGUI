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
from cardata import CarData, NAMESTRING, NAMESTRING_MAXLEN

import ctypes
PROCESS_PER_MONITOR_DPI_AWARE = 2
ctypes.windll.shcore.SetProcessDpiAwareness(PROCESS_PER_MONITOR_DPI_AWARE)

'''
TODO:
    - investigate dpi scaling when combining tkinter and matplotlib
    - add awd slider for center diff (current assumption is 60%)
    - override slider to add ability to enter ratio
    - add information on shifts
    - add duration for gear at full throttle and no traction issues
    - investigate torque output during a shift
    - maybe replace matplotlib slider with tkinter slider
    - add dump to excel file for all variables
    - rewrite to use pyqtgraph and qt due to limitations in tkinter/matplotlib
    - consider https://matplotlib.org/stable/api/scale_api.html#matplotlib.scale.FuncScale
    - consider https://matplotlib.org/stable/tutorials/intermediate/autoscale.html
    - consider  tkinter.font.measure(text)
      Pass this method a string, and it will return the number of pixels of width that string will take in the font. Warning: some slanted characters may extend outside this area. 

moving the matplotlib sliders into their own canvas resulted in the main canvas
not updating. May be due to a lack of an update call:
        self.canvas.draw() seems to be far slower than fig.canvas.draw_idle()
        self.canvas.draw() #should be called every update, doesn't seem to be required at all?
'''

def main ():
    Window()

# suppress matplotlib warning while running in thread
# import warnings
# warnings.filterwarnings("ignore", category=UserWarning)

#unused lowpass filter code
#see https://stackoverflow.com/questions/63320705/what-are-order-and-critical-frequency-when-creating-a-low-pass-filter-using
# from scipy.signal import butter, lfilter#, freqz
# def butter_lowpass(cutoff, fs, order=5):
#     return butter(order, cutoff, fs=fs, btype='low', analog=False)

# def butter_lowpass_filter(data, cutoff, fs, order=5):
#     b, a = butter_lowpass(cutoff, fs, order=order)
#     y = lfilter(b, a, data)
#     return y

# #accel_filtered = butter_lowpass_filter(accel, cutoff, fs, order)

# # Filter requirements.
# order = 6  #higher is steeper, 
# fs = 60.0       # sample rate, Hz
# cutoff = 5.00  # desired cutoff frequency of the filter, Hz

class Window ():
    width, height = 1550, 1030
    graph_height, graph_width = 1200, 1000
    slider_height, slider_width = 500, 550
    frameinfo_height = 400
    
    DEFAULT_CAR_ORDINAL = 2352 #Acura NSX 2017
    DEFAULT_CAR_PI = 831       #stock PI
    DEFAULTCARDATA =  CarData.getinfo(DEFAULT_CAR_ORDINAL)
    DEFAULTCARDATA.update({'car_performance_index':DEFAULT_CAR_PI})
    DEFAULTCAR = NAMESTRING(DEFAULTCARDATA)
    
    TRACE_DIR = 'traces/'

    def __init__(self):
        self.root = tkinter.Tk()
      #  self.root.tk.call('tk', 'scaling', 2) #Spyder console fix for DPI too low
        self.root.title("Interactive gearing for collected traces for ForzaGUI")

        self.__init__carlist()     
        
        self.__init__combobox()
        self.__init__filter_button()        
        self.__init__main_frame()        
        self.__init__notebook()                
        self.__init__widget_placement()
        
        self.carname_changed() #force initial update to default car
        
        self.root.geometry(f"{self.width}x{self.height}") #must be set after creating the gearing canvas?
        self.root.minsize(self.width, self.height)        
        self.root.mainloop()
    
    def __init__combobox(self):
        self.combobox = tkinter.ttk.Combobox(self.root, 
                                             width=NAMESTRING_MAXLEN,
                                             exportselection=False, 
                                             state='readonly',
                                             values=sorted(self.carlist.keys())
                                             )
        index = sorted(self.carlist.keys()).index(self.DEFAULTCAR)
        self.combobox.current(index)
        self.combobox.bind('<<ComboboxSelected>>', self.carname_changed)
        
    def __init__filter_button(self):
        self.filter_var = tkinter.IntVar(value=1)
        self.filter_button = tkinter.Checkbutton(self.root, 
                                                 text='Filter old traces', 
                                                 variable=self.filter_var, 
                                                 command=self.filter_toggle,
                                                 onvalue=1, offvalue=0)
    
    def __init__main_frame(self):
    #    self.frame = tkinter.Frame(self.root)
        px = 1/plt.rcParams['figure.dpi'] # pixel in inches
        self.fig = Figure(figsize=(self.graph_width*px, self.graph_height*px), 
                          dpi=72, layout="constrained")
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.root)
        self.fig_slider = Figure(figsize=(self.slider_width*px, 
                                          self.slider_height*px), dpi=72)
        self.canvas_slider = FigureCanvasTkAgg(self.fig_slider, 
                                               master=self.root)
        self.toolbar = NavigationToolbar2Tk(self.canvas, self.root, 
                                            pack_toolbar=False)
    
    def __init__notebook(self):
        self.notebook = tkinter.ttk.Notebook(self.root)
        self.frame_info = tkinter.Frame(self.notebook)
        self.info = InfoFrame()
        self.info.set_canvas(self.frame_info)       
        self.power_graph = PowerGraph(self.notebook)
        self.torque_deriv_graph = TorqueDerivative(self.notebook)
        self.slip_ratio = SlipRatio(self.notebook)
        self.dragtorquegraph = DragTorqueGraph(self.notebook)
        self.intersections = Intersections(self.notebook)
        self.notebook.add(self.frame_info, text="Statistics")
        self.notebook.add(self.power_graph.frame, text='Power')
        self.notebook.add(self.torque_deriv_graph.frame, text='Torque\'')
        self.notebook.add(self.slip_ratio.frame, text='Slip ratio')
        self.notebook.add(self.dragtorquegraph.frame, text='Drag/Torque')
        self.notebook.add(self.intersections.frame, text='Shiftrpms')
    
    def __init__widget_placement(self):
        self.root.grid_rowconfigure(1, minsize=self.slider_height, 
                                       weight=self.slider_height)
        self.root.grid_rowconfigure(2, minsize=self.frameinfo_height, 
                                       weight=self.frameinfo_height)
        self.root.grid_columnconfigure(0, minsize=self.slider_width, 
                                          weight=self.slider_width)
        self.root.grid_columnconfigure(1, minsize=self.graph_width, 
                                          weight=self.graph_width)
        
        self.combobox.grid(row=0, column=0, columnspan=2)
        self.filter_button.grid(row=0, column=0, columnspan=2, 
                                sticky=tkinter.E)
        self.canvas_slider.get_tk_widget().grid(row=1, column=0, 
                                                sticky=tkinter.NSEW)
        self.canvas.get_tk_widget().grid(row=1, column=1, rowspan=2, 
                                         sticky=tkinter.NSEW)
        self.notebook.grid(row=2, column=0, sticky=tkinter.NSEW)
        self.toolbar.grid(row=3, column=0, columnspan=2, sticky=tkinter.NSEW)
        
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
        trace.array = (trace.array[:Trace.REMOVE_FROM_START] + #start
                      trace.array[Trace.REMOVE_FROM_START:-1:decimator] +  
                      [trace.array[-1]]) #force last element
        trace.finish()

        final_ratio = Sliders.average_final_ratio(trace.gears)

        self.fig.clf()
        if self.fig_slider is not None:
            self.fig_slider.clf()
        self.gearing = Gearing(trace, self.fig, final_ratio=final_ratio, 
                               title=carname, fig_slider=self.fig_slider)
        
        self.drag = DragDerivation(trace=None, filename=filename)
        self.drag.draw_torquelosttodrag(ax=self.gearing.ax, 
                                        step_kmh=Gearing.STEP_KMH, 
                                        **self.drag.__dict__)
        
        self.info.carname_changed(carname, packet=None, trace=trace, 
                                  drag=self.drag)
        self.frame_info.update() #required since adding Notebook layer
        self.power_graph.carname_changed(trace=trace)
        self.torque_deriv_graph.carname_changed(trace=self.drag)
        self.slip_ratio.carname_changed(trace=trace)
        self.dragtorquegraph.carname_changed(drag=self.drag)
        self.intersections.carname_changed(drag=trace)
        
    #filename structure:
    def __init__carlist(self):
        self.carlist = {}
        self.carlist_all = {}
        for entry in os.scandir(self.TRACE_DIR):
            filename = entry.name
            ordinal = int(filename.split('_')[1][3:])
            pi = int(filename.split('_')[2][2:-5])
            filepath = self.TRACE_DIR + filename

            data = CarData.getinfo(ordinal)
            if data is not None:
                data.update({'car_performance_index':pi})
                carname = NAMESTRING(data)
                trace = Trace(fromfile=True, filename=filepath)
                self.carlist_all[carname] = filepath
                if len(trace.data) > 0:
                    self.carlist[carname] = filepath
            else:
                print(f'ordinal {ordinal} NOT FOUND')
        print(f'filtered car list contains {len(self.carlist)} items')
        print(f'total car list contains {len(self.carlist_all)} items')

class NotebookFrame():
    FIG_X, FIG_Y = 546, 328
    def __init__(self, frame):
        self.frame = tkinter.Frame(frame)
        px = 1/plt.rcParams['figure.dpi'] # pixel in inches
        self.fig = Figure(figsize=(self.FIG_X*px, self.FIG_Y*px), dpi=72, 
                          layout="constrained")
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.frame)
        self.canvas.get_tk_widget().pack(fill='both', expand=True)
    
    def draw_idle(self):
        self.canvas.draw_idle()

class PowerGraph(NotebookFrame):
    def carname_changed(self, trace):
        self.fig.clf()
        ax = self.fig.subplots(1)
        ax.plot(trace.rpm, trace.power)
        ax.grid()
        self.kw = self.fig.text(0.00, 0.00, "kW / RPM")
        for item in ([ax.title, ax.xaxis.label, ax.yaxis.label] +
             ax.get_xticklabels() + ax.get_yticklabels()):
            item.set_fontsize(8)
        self.draw_idle()

#focuses on the numeric derivative of torque after peak power is reached
#discounting noise, it can be observed that some cars have a linear drop in 
#torque while others have a gentle quadratic slope.
class TorqueDerivative(NotebookFrame):
    def carname_changed(self, trace):
        self.fig.clf()
        ax = self.fig.subplots(1)
        i = np.argmax(trace.power)
        torque_deriv = np.gradient(trace.torque, trace.rpm)[i:]
                
        ymin = np.percentile(torque_deriv, 5)
        ymax = np.percentile(torque_deriv, 95)
        
        if (np.isnan(ymin) or np.isnan(ymax) or 
            np.isinf(ymin) or np.isinf(ymax)):
            print("TorqueDerivative failed on ymin/ymax")
            return
        
        torque_deriv_filtered = torque_deriv[(torque_deriv > ymin) & 
                                             (torque_deriv < ymax)]
        ax.plot(torque_deriv_filtered)
        ax.grid()
        ax.set_ylim(ymin, ymax)
        ax.set_xlabel("Nm' / points  5/95% filtered derivative of torque past peak power")
        for item in ([ax.title, ax.xaxis.label, ax.yaxis.label] +
             ax.get_xticklabels() + ax.get_yticklabels()):
            item.set_fontsize(8)
        self.draw_idle()

#derives slip ratio during trace and relates it to the normalized slip ratio in
#the packets.
class SlipRatio(NotebookFrame):
    TIRES = ['FL', 'FR', 'RL', 'RR']
    
    def carname_changed(self, trace):
        if trace.version < 2:
            return
        self.fig.clf()
        ax = self.fig.subplots(1)
        data = trace.data_to_fdp()
        sizes = ([float(trace.carinfo.get('wheelsize_front', 0)) / 100] * 2 + 
                 [float(trace.carinfo.get('wheelsize_rear',  0)) / 100] * 2)
        for tire, size in zip(self.TIRES, sizes):
            x,y = zip(*self.get_slipratio_for_wheel(tire, size, data))
            ax.scatter(x[20:],y[20:], label=tire, s=2)
        ax.legend()
        ax.grid()
        ax.set_xlabel("game normalized slip ratio")
        ax.set_ylabel("calculated slip ratio")
        self.draw_idle()
    
    @staticmethod
    def get_slipratio_for_wheel(tire, size, data):
        output = []
        for p in data:
            base_rotation_speed = p.speed / size
            rotation_speed = getattr(p, f'wheel_rotation_speed_{tire}')
            slip_ratio = getattr(p, f'tire_slip_ratio_{tire}')
            output.append((slip_ratio, rotation_speed / base_rotation_speed))
            
        return output

class DragTorqueGraph(NotebookFrame):
    def carname_changed(self, drag):
        self.fig.clf()
        ax = self.fig.subplots(1)
        
        ax.plot([x*drag.torque_adj[drag.CUT]/drag.speed_gradient[drag.CUT] 
                 for x in drag.speed_gradient], label='accel scaled to torque')
        ax.plot(drag.torque_adj[1:-1], label='torque in collected gear')
        xmin, xmax = ax.get_xlim()
        ax.set_xlim(0, xmax)
        ymin, ymax = ax.get_ylim()
        ax.vlines(drag.CUT, 0, ymax, linestyle=':')
        ax.set_xlabel('points')
        ax.legend()
        ax.grid()
        
        self.draw_idle()

#from scipy.signal import savgol_filter
from scipy import interpolate
class Intersections(NotebookFrame):
    DIVISOR = 2 #TODO: create variable divisors for x and y ticks
    def carname_changed(self, drag):
        self.carname_changed_intersections(drag)
        self.carname_changed_graph()
        
    def carname_changed_intersections(self, drag):
        self.rel_ratios = self.set_relratios(drag.gears)
        self.rpm_limit = drag.rpm[-1]
        
        rpm = drag.rpm
        power = drag.power
        
        ratios = np.flip(np.linspace(2, 1, 200, False))
        ratios = ratios[ratios >= 1.01]
        
        shiftrpms = []
        for ratio in ratios:
            intersection = intersect.intersection(rpm, power, 
                                                  rpm*ratio, power)[0]
            if len(intersection):
                shiftrpms.append(intersection[-1])
            else:
                shiftrpms.append(rpm[-1])
                break
        self.ratios = ratios[:len(shiftrpms)]
        self.shiftrpms = shiftrpms
        
        # self.shiftrpms = interpolate.interp1d(ratios, shiftrpms, 
        #                                       bounds_error=False, 
        #                                       fill_value=(shiftrpms[0], 
        #                                                   rpm[-1]))
    def carname_changed_graph(self):
        self.fig.clf()
        ax = self.fig.subplots(1)
        
        ratios = self.ratios
        shiftrpms = self.shiftrpms
        
        ax.plot(ratios, shiftrpms)
    #    ax.plot(ratios, apply_savgol(shiftrpms))
        # ax.set_xticks(np.linspace(1, 2, 50, False))    
        ax.set_xlim(1.01, ratios[-1])
        ax.set_xticks(ratios[0::2*self.DIVISOR])
        
        # ymin, ymax = shiftrpms[0], shiftrpms[-1]
        ymin, ymax = min(shiftrpms), max(shiftrpms)
        ymin = 25*int(ymin/25)
        ymax = 25*math.ceil(ymax/25)
        ax.set_ylim(ymin, ymax)
        ycount = int((ymax - ymin) / 25)
        ax.set_yticks(np.linspace(ymin, ymax, ycount+1, True)[::self.DIVISOR])    
        ax.tick_params(axis='x', labelrotation = 270)
   #     plt.xticks(rotation=270)
        ax.grid()
        for item in ([ax.title, ax.xaxis.label, ax.yaxis.label] +
             ax.get_xticklabels() + ax.get_yticklabels()):
            item.set_fontsize(7)
        
        self.draw_idle()
    
    def get(self):
        shiftrpms = self.shiftrpms(self.rel_ratios)
        return [min(rpm, self.rpm_limit) for rpm in shiftrpms]
    
    def set_rpmlimit(self, value):
        self.rpm_limit = value
    
    def set_relratios(self, ratios):
        self.rel_ratios = [x/y for x,y in zip(ratios[:-1], ratios[1:])]
        
        #apply savgol to shiftrpms?
        #have other call that function
    
    #savitsky-golay
    #Keep in mind that in order to have your Savitzky-Golay filter working properly, 
    #you should always choose an odd number for the window size and the order of 
    #the polynomial function should always be a number lower than the window size.
    # @staticmethod
    # def apply_savgol(array):
    #     window_length = 13
    #     polyorder = 2
    #     return savgol_filter(array, window_length, polyorder)

class InfoFrame():
    DEFAULT_CENTERDIFF = 70
    CARNAME_FONTSIZE = 7
    TABLE_FONTSIZE = 8
    DRIVETRAINS = ['FWD', 'RWD', 'AWD'] #TODO: to constants?
    
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
                ['Peak power:', self.peak_power_var, 'kW @', 
                                               self.peak_power_rpm_var, 'rpm'], 
                ['Peak torque:', self.peak_torque_var, 'Nm @', 
                                              self.peak_torque_rpm_var, 'rpm'],
                ['Peak boost:', self.peak_boost_var, 'bar'],
                ['Revlimit:', self.revlimit_var, ''],
                ['Engine:', self.engine_idle_rpm_var, 'rpm idle,', 
                                           self.engine_max_rpm_var, 'rpm max'],
                ['Num cylinders:', self.num_cylinders_var, ''], 
                ['Top speed:', self.top_speed_var, 'km/h'],
                ['vmax:', self.true_top_speed_var, 'km/h @', 
                                       self.true_top_speed_ratio_var, 'ratio'],
                ['Drag value:', self.drag_var,' (100*C*wheelsize*efficiency)'],
                ['Drivetrain:', self.drivetrain_var, ''],
                ['Drivetrain loss:', self.transmission_efficiency_var, '%'],
                ['Wheel radius:', self.wheelsize_front_var, 'front,', 
                                         self.wheelsize_rear_var, 'rear (cm)'],
                # ['Shift duration:', self.shiftdelay_var, 'seconds'],
                ['Stock weight:', self.weight_var, 'kg'],
                # ['Center diff:', self.center_diff_var, '% to rear if AWD'],
                # ['Max slip ratio:', self.max_slipratio_front_var, '% front, ', self.max_slipratio_rear_var, '% rear']
                # ['Torque limit:', self.torque_limit_var, 'Nm']
            ]
        
    #    entry_centerdiff_validation = self.root.register(Window.entry_centerdiff_validation)
        
        opts.update({'font': tkinter.font.Font(size=self.TABLE_FONTSIZE)})
        carname_opts = opts.copy()
        carname_opts['font'] = tkinter.font.Font(size=self.CARNAME_FONTSIZE)
        tkinter.Label(frame, textvariable=table[0], **carname_opts).grid(
                               row=0, column=0, columnspan=6, sticky=tkinter.W)
        for i, row in enumerate(table[1:], start=1):
            tkinter.Label(frame, text=row[0], **opts).grid(row=i, column=0, 
                                                           sticky=tkinter.E)
            tkinter.Label(frame, textvariable=row[1], **opts).grid(row=i, 
                                                                   column=1)
            if len(row) == 3:
                tkinter.Label(frame, text=row[2], **opts).grid(
                               row=i, column=2, columnspan=3, sticky=tkinter.W)
            else:
                tkinter.Label(frame, text=row[2], **opts).grid(
                                             row=i, column=2, sticky=tkinter.W)
                tkinter.Label(frame, textvariable=row[3], **opts).grid(
                                                               row=i, column=3)
                tkinter.Label(frame, text=row[4], **opts).grid(
                                             row=i, column=4, sticky=tkinter.W)

        #round to nearest 25 #maybe use elsewhere?
     #  self.revlimit_var.set(int(25*round(drag.rpm[-1]/25, 0))) 
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
                carname = NAMESTRING(cardata)
                self.weight_var.set(cardata['weight'])
            self.carname_var.set(carname)
        
        if packet is not None: #or trace_v2            
            self.num_cylinders_var.set(packet.num_cylinders)
            self.engine_idle_rpm_var.set(int(round(packet.engine_idle_rpm, 0)))
            self.engine_max_rpm_var.set(int(round(packet.engine_max_rpm, 0))) 
            self.drivetrain_var.set(self.DRIVETRAINS[packet.drivetrain_type])
        
        if trace is not None: #trace_v0plus
            source = drag if drag is not None else trace
            peak_power_index = np.argmax(source.power)
            self.peak_power_var.set(round(max(source.power), 1))
            self.peak_power_rpm_var.set(int(source.rpm[peak_power_index]))
            peak_torque_index = np.argmax(source.torque)
            self.peak_torque_var.set(round(max(source.torque), 1))
            self.peak_torque_rpm_var.set(int(source.rpm[peak_torque_index]))
            self.revlimit_var.set(math.ceil(source.rpm[-1]))
            self.top_speed_var.set(round(drag.top_speed_by_drag(
                                                          **drag.__dict__), 1))
            gear_ratio, top_speed = drag.optimal_final_gear_ratio(
                                                               **drag.__dict__)
            self.true_top_speed_var.set(round(top_speed, 1))
            self.true_top_speed_ratio_var.set(round(gear_ratio, 3))
        
        if packet is None and trace_v1plus:
            self.drivetrain_var.set(trace.carinfo.get('drivetrain_type','N/A'))
        
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
                wheelsize = (
                        (1-InfoFrame.DEFAULT_CENTERDIFF/100)*wheelsize_front 
                         + InfoFrame.DEFAULT_CENTERDIFF/100*wheelsize_rear)
                self.center_diff_var.set(InfoFrame.DEFAULT_CENTERDIFF)
                # self.centerdiffentryenabled(True)

            shift_delay = trace.carinfo.get('shiftdelay', 0)
            shift_delay = f"±{shift_delay/60:.3f}" if shift_delay!=0 else 'N/A'
            self.shiftdelay_var.set(shift_delay)

        if (trace_v1plus and packet) or trace_v2:
            if (wheelsize not in ['N/A', 0] and 
                self.weight_var.get() not in ['N/A', 0]):
                efficiency = 1/statistics.median((drag.torque_adj - drag.C*drag.speed*drag.speed)/wheelsize/drag.accel/self.weight_var.get())
            else:
                efficiency = 0
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
        for key, var in self.__dict__.items():
            if key[-4:] == '_var':
                var.set('N/A')
            
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
            max_torque.extend([wheel_force/getattr(p,f'tire_slip_ratio_{tire}')
                                                            for tire in tires])
            low = int(len(max_torque)/20)
            high= int(len(max_torque)/10)
        torque_limit = statistics.median(sorted(max_torque)[low:high])
        print(sorted(max_torque)[low:high])
        self.torque_limit_var.set(int(torque_limit))

    #TODO: investigate
    def derive_max_slipratio(self, data, wheelsize_front, wheelsize_rear, 
                                                              drawgraph=False):
        wheelsize = {'FL': wheelsize_front/100, 'FR': wheelsize_front/100,
                     'RL': wheelsize_rear/100, 'RR': wheelsize_rear/100}
        tiredata = {}
        if drawgraph:
            fig, ax = plt.subplots()
        count = len(data)
        ymin, ymax = 1, 0
        for tire in ['FL', 'FR', 'RL', 'RR']:
            val = [(wheelsize[tire] / (p.speed / 
                    getattr(p, f'wheel_rotation_speed_{tire}')) - 1) / 
                    getattr(p, f'tire_slip_ratio_{tire}') for p in data]
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
        y = [x*full_ratio for x,y in zip(self.trace.torque, self.trace.rpm) 
                                                         if y <= self.rpmlimit]
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
    
    def __init__(self, trace, fig=None, final_ratio=1, title=None, 
                 fig_slider=None,car_ordinal=None, car_performance_index=None):
        if fig == None:
            self.fig, (self.ax, ax2) = plt.subplots(2,1, 
                                          gridspec_kw={'height_ratios': [2,1]})
            self.fig.set_size_inches(16, 10)
            self.fig.tight_layout() #changed to constrained layout when Figure is defined
        else:
            self.fig = fig
            self.ax, ax2 = self.fig.subplots(2,1,
                                          gridspec_kw={'height_ratios': [2,1]})

        self.__init__graph(trace, final_ratio, title, car_ordinal, 
                           car_performance_index)
        self.__init__power_contour()
        
        #force add legend to axis due to extra legend being added later
        #see https://matplotlib.org/stable/tutorials/intermediate/legend_guide.html
        self.legend = self.ax.legend()  
        self.ax.add_artist(self.legend) 
        
        #separate_fig refers to splitting the slider figure from the graph
        separate_fig = True
        if fig_slider == None:
            fig_slider = self.fig
            separate_fig = False        
        
        self.sliders = Sliders(fig_slider, self.final_ratio, self.gears, 
                               self.trace, self.xmax, self.rpmperkmh, 
                               separate_fig)
        self.sliders.final_ratio_onchanged(self.update_final_ratio)
        self.sliders.rpmlimit_onchanged(self.update_rpmlimit)
        self.sliders.integral_onchanged(self.update_integral)
        
        self.shiftrpm = ShiftRPM(fig_slider, self.ax, self.gears, self.legend, 
                                 self.fig.canvas.draw_idle)
        
        self.differencegraph = DifferenceGraph(ax2, self.gears, 
                                               self.power_contour, 
                                               self.rpmperkmh, self.xmax, 
                                               self.xticks)
        
        #TODO: move integral text to DifferenceGraph?
        fig_text = fig_slider if fig_slider is not None else fig 
        self.integral_text = fig_text.text(*Sliders.axes['integral_text'], 
                                           "Gearing efficiency: 100% in range")
        
        self.disclaimer = fig_text.text(*Sliders.axes['disclaimer'], 'Shift rpm values valid if and only if: \nFull throttle, shift duration is 0, no traction limit')
        
        self.print_integral()

    def __init__graph(self, trace, final_ratio, title, car_ordinal, 
                      car_performance_index):
        self.trace = trace
        self.final_ratio = final_ratio
        self.trace.gears = [g/final_ratio for g in self.trace.gears]

        self.gears = []
        for i, ratio in enumerate(self.trace.gears):
            self.gears.append(Gear(i, trace, self.ax, self.update,final_ratio))
        
        #sort rpm and torque to be monotonically increasing on rpm
        rpm, torque = zip(*sorted(zip(self.trace.rpm, self.trace.torque)))
        self.trace.rpm = np.array(rpm)
        self.trace.torque = np.array(torque)

        #1 km/h per x rpm, scaled to final ratio
        self.rpmperkmh = (statistics.median([(a/b) 
               for (a, b) in zip(self.trace.rpm, self.trace.speed)]) /
              (self.trace.gears[self.trace.gear_collected-1]*self.final_ratio))
        valstep = Gearing.STEP_KMH*self.rpmperkmh

        #if the x values are converted to speed, we seem to lose accuracy in 
        #drawing the power contour. therefore, use rpm/ratio and hide the 
        #xtick true values
        self.xmax = math.ceil(self.trace.rpm[-1]/
                              (self.gears[-1].ratio*self.final_ratio)
                              *valstep)/valstep
        self.xticks = np.arange(0,self.xmax+valstep,valstep)

        ymax = max(self.trace.torque*self.gears[0].ratio*self.final_ratio)*1.01
        self.ax.set_ylim(0, ymax)
        self.ax.set_xlim(0, self.xmax)
        self.ax.set_xticks(self.xticks)
        self.ax.set_xlabel("speed (km/h)")
        self.ax.set_ylabel("torque (Nm)")
        self.ax.set_xticklabels([math.ceil(x/self.rpmperkmh) 
                                                         for x in self.xticks])
        
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

    def __init__power_contour(self):
        i = self.trace.power.argmax()
        peak_power_torque = self.trace.torque[i]
        peak_power_rpm = self.trace.rpm[i]

        self.power_contour = lambda rpm: peak_power_torque*peak_power_rpm/rpm
        rpmmax = int(2*self.trace.rpm[-1])
        self.ax.plot(self.power_contour(range(1, rpmmax)), 
                     label='Peak power torque')

    def update_integral(self, value):
        self.sliders.lower, self.sliders.upper = value
        self.print_integral()
    
    #TODO: investigate: integral answer is questionable
    def print_integral(self):
       x,y = self.differencegraph.get_difference()
       lower = self.sliders.lower*self.rpmperkmh
       upper = self.sliders.upper*self.rpmperkmh
       y = [b+self.power_contour(a) for a, b in zip(x, y) 
                                                  if a >= lower and a <= upper]
       x = [a for a in x if a >= lower and a <= upper]
       
       maximum = math.log(upper/lower)*self.power_contour(1)
       #print(x, y)
       integral = np.trapz(y, x)
       percentage = 100*integral/maximum
       self.integral_text.set_text(
                            f"Gearing efficiency: {percentage:5.1f}% in range")
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
        for text, gear, next_gear in zip(self.sliders.rel_ratios_text, 
                                         self.gears[:-1], self.gears[1:]):
            text.set_text(f'{gear.ratio/next_gear.ratio:.3f}')

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

    def __init__(self, fig, final_ratio, gears, trace, xmax, rpmperkmh, 
                 separate_fig=False):
        if separate_fig:
         #   Sliders.xmin, Sliders.xmax = 0.2, 1.1
            Sliders.axes = {
                'final_gear':            [0.17, 0.95,           0.74, 0.025],
                'gears':       lambda g: [0.17, 0.90-0.06*g,    0.74, 0.025],
                'rel_ratios':  lambda g: [0.82, 0.87-0.06*g],
                'reset':                 [0.7, 0.27,            0.2, 0.08],
                'rpmlimit':              [0.18, 0.22,           0.7, 0.025],
                'integral':              [0.18, 0.16,           0.6, 0.025],
                'integral_text':         [0.21, 0.13],
                'checkbutton':           [0.21, 0.00, 0.2, 0.2],
                'disclaimer':            [0.01, 0.01] }
        else:
            # create space for sliders
            fig.subplots_adjust(left=self.xmax)

        self.__init__gearsliders(fig, final_ratio, gears, trace)
        self.__init__rel_ratios(fig, gears)
        self.__init__resetbutton(fig, gears)
        self.__init__rpmlimitslider(fig, trace)
        self.__init__integralslider(fig, final_ratio, gears, trace, xmax, 
                                    rpmperkmh)
    
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

        #connect sliders: the ratio per slider must be between previous 
        #and next gear's ratios            
        for a, b in zip(gears[:-1], gears[1:]):
            b.slider.slidermax = a.slider
            a.slider.slidermin = b.slider

    def __init__rel_ratios(self, fig, gears):
        self.rel_ratios_text = []
        for gear, next_gear in zip(gears[:-1], gears[1:]):
            text = fig.text(*self.axes['rel_ratios'](gear.gear), 
                                          f'{gear.ratio/next_gear.ratio:.3f}')
            self.rel_ratios_text.append(text)
    
    #Create a matplotlib.widgets.Button to reset the sliders to initial values.
    def __init__resetbutton(self, fig, gears):
        self.ax_reset = fig.add_axes(self.axes['reset'])
        self.button = Button(self.ax_reset, 'Reset', hovercolor='0.975')
        def reset(event):
            self.final_gear_slider.reset()
            self.rpmlimit_slider.reset()
            for graph in gears:
                graph.slider.reset()
        self.button.on_clicked(reset)
    
    #create slider to limit rpm/torque graph to the defined rpm limit 
    #(think redline limit for automatic transmission)
    def __init__rpmlimitslider(self, fig, trace):
        self.rpmlimit_ax = fig.add_axes(self.axes['rpmlimit'])
        self.rpmlimit_slider = Slider(
            ax=self.rpmlimit_ax,
            label='RPM limit',
            valmin=trace.rpm[0],
            valmax=trace.rpm[-1],
            valinit=trace.rpm[-1],
         #   valstep = 50
        )
        
    def __init__integralslider(self, fig, final_ratio, gears, trace, xmax, 
                                                                    rpmperkmh):
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
        
    def final_ratio_onchanged(self, func):
        self.final_gear_slider.on_changed(func)    
        
    def rpmlimit_onchanged(self, func):
        self.rpmlimit_slider.on_changed(func)
    
    def integral_onchanged(self, func):
        self.integral_slider.on_changed(func)

    @classmethod
    def slider_limits(cls, final_ratio):
        if final_ratio == 1:
            final_slider_settings = {
                            'valmin': cls.FINALRATIO_MIN / cls.FINALRATIO_MAX,
                            'valmax': cls.FINALRATIO_MAX / cls.FINALRATIO_MIN }
            gear_slider_settings = {
                            'valmin': cls.FINALRATIO_MIN * cls.GEARRATIO_MIN,
                            'valmax': cls.FINALRATIO_MAX * cls.GEARRATIO_MAX }
        else:
            final_slider_settings = {'valmin': cls.FINALRATIO_MIN,
                                     'valmax': cls.FINALRATIO_MAX }
            gear_slider_settings = {'valmin': cls.GEARRATIO_MIN,
                                    'valmax': cls.GEARRATIO_MAX }

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
        self.draw_func = draw_func
                
        self.ax = fig.add_axes(Sliders.axes['checkbutton']) 
        self.ax.axis('off') #remove black border around axis
        self.buttons = CheckButtons(self.ax, ["Display shift RPM lines"], 
                                    actives=[ShiftRPM.DEFAULTSTATE])
        self.buttons.on_clicked(self.set_visibility)
        
        _, self.ymax = self.ax_graph.get_ylim()
        intersections = self.get_intersections()
        self.vlines = [ax_graph.vlines(i, 0.0, self.ymax, linestyle=':') 
                                    for i, g in zip(intersections, self.gears)]
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
            shiftrpm = i * g.final_ratio * g.ratio
            t.set_text(f"Gear {g.gear+1}, shift at {shiftrpm:5.0f} rpm")

        if not all(self.buttons.get_status()): #assumes single checkbutton
            return

        for x, vline in zip(intersections, self.vlines):
            vline.set_segments([np.array([[x, 0.0],[x, self.ymax]])])
        
    def get_intersections(self):
        X = 0 #axis
        data = [graph.get_points() for graph in self.gears]
        intersections = [intersect.intersection(x1, y1, x2, y2)[X] 
                             for (x1,y1), (x2, y2) in zip(data[:-1], data[1:])]
        intersections = [i[-1] if len(i) > 0 else x[-1] 
                                      for i, (x,y) in zip(intersections, data)]
        
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
        intersections = self.get_intersections()   
        
        min_rpm = data[0][X][0] #initial rpm of first gear
        max_rpm = data[-1][X][-1] #final rpm of final gear
        
        intersections = [min_rpm] + intersections + [max_rpm]
        x_array, y_array = [], []
        for start, end, (x,y) in zip(intersections[:-1], 
                                     intersections[1:], data):
            x_array.extend([rpm for rpm in x if rpm >= start and rpm <= end])
            y_array.extend([torque - self.power_contour(rpm)
                                for rpm, torque in zip(x,y) 
                                if rpm >= start and rpm <= end])
        return (x_array, y_array)

    def get_intersections(self):
        X = 0
        data = [graph.get_points() for graph in self.gears]
        intersections = [intersect.intersection(x1, y1, x2, y2)[X] 
                             for (x1,y1), (x2, y2) in zip(data[:-1], data[1:])]
        intersections = [i[0] if len(i) > 0 else x[-1] 
                                      for i, (x,y) in zip(intersections, data)]
        return intersections
    
    def redraw_difference(self):
        x_array, y_array = self.get_difference()
        
        #convert to percentage of optimal
        y_array = [100*y/self.power_contour(x) for x,y in zip(x_array,y_array)]
        #y_array = sorted(y_array)

        if self.fillplot is not None:
            self.fillplot.remove()
        self.fillplot = self.ax.fill_between(x_array, y_array, color='b')
        #    self.diffplot.remove()
        #    self.diffplot, = self.ax2.plot(x_array, y_array, 'b')

if __name__ == "__main__":
    main()
# -*- coding: utf-8 -*-
"""
Created on Fri Oct 28 18:48:33 2022

@author: RTB
"""

import numpy as np
import math
import statistics
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, RangeSlider, Button
import intersect

from dragderivation import Trace, DragDerivation
from guicarinfo import CarData

'''
TODO:
    - add metric of power lost vs optimal
    - maybe add slider of vmin and vmax for metric of power lost vs optimal
    - add redline slider that limits each gear to x rpm maximum
    - add awd slider for center diff (current assumption is 60%)
    - override slider to add ability to enter ratio
    - add relative ratio between ratios
    - add information on shifts
    - add duration for gear at full throttle and no traction issues
    - investigate torque output during a shift
    - split matplotlib drawings into separate canvases
    - maybe replace matplotlib slider with tkinter slider
    - investigate status bar not displaying x axis
'''

def main ():
    global window #trace, gearing, car_ordinal, car_performance_index

    #example: stock NSX Acura
    # car_ordinal = 2352
    # car_performance_index = 831
    # filename = f'traces/trace_ord{car_ordinal}_pi{car_performance_index}.json'

    # override_gearratio = [] #e.g.: [4.14, 2.67, 1.82, 1.33, 1.00, 0.8]
    # final_ratio = 1
    # trace = Trace(fromfile=True, filename=filename)

    # if len(override_gearratio):
    #     trace.gears = override_gearratio
    #     trace.gears = [x*final_ratio for x in trace.gears]

#    gearing = Gearing(trace, None, final_ratio, car_ordinal, car_performance_index)

    window = Window()

#helper class for class Gearing
#every gear drawn by Gearing
class Gear():
    def __init__(self, gear, trace, ax, update_backref, final_ratio=1):
        self.gear, self.trace = gear, trace
        self.ratio = trace.gears[gear]
        self.final_ratio = final_ratio
        self.update_backref = update_backref
        x,y = self.get_points()
        self.plot, = ax.plot(x, y, label=f'Gear {gear+1}')

    def get_points(self):
        full_ratio = self.ratio*self.final_ratio
        x = [x/full_ratio for x in self.trace.rpm]
        y = [x*full_ratio for x in self.trace.torque]
        return (x,y)

    def add_slider(self, ax, slider):
        self.ax, self.slider = ax, slider

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

import os
import tkinter
import tkinter.ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
# suppress matplotlib warning while running in thread
import warnings
warnings.filterwarnings("ignore", category=UserWarning)

class Window ():
    width = 1500
    height = 1000

    DEFAULTCAR = 'Acura NSX (2017) PI:831 MODERN SUPERCARS'
    TRACE_DIR = 'traces/'

    def __init__(self):
        self.root = tkinter.Tk()
     #   self.root.tk.call('tk', 'scaling', 1.0) #Spyder console fix for DPI too low
        self.root.title("Interactive gearing for collected traces for ForzaGUI")
        self.root.geometry(f"{Window.width}x{Window.height}")

        self.frame = tkinter.Frame(self.root)

        self.generate_carlist()

        self.combobox = tkinter.ttk.Combobox(self.frame, width=80,
                                             exportselection=False, state='readonly',
                                             values=sorted(self.carlist.keys()))
        index = sorted(self.carlist.keys()).index(Window.DEFAULTCAR)
        self.combobox.current(index)
        self.combobox.bind('<<ComboboxSelected>>', self.carname_changed)
        
        px = 1/plt.rcParams['figure.dpi'] # pixel in inches
        self.fig = Figure(figsize=(Window.width*px, (Window.height-72)*px))
    #    self.fig = Figure(figsize=(16, 10), dpi=72)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.frame)
        self.canvas.draw() #should be called every update, doesn't seem to be required

        self.toolbar = NavigationToolbar2Tk(self.canvas, self.root, pack_toolbar=False)
        self.toolbar.update()

        self.__init__frame_info()

        self.carname_changed()

        self.frame.pack(fill='both', expand=True)
        self.combobox.pack()
        self.canvas.get_tk_widget().pack(fill='both', expand=True)#, anchor=tkinter.W)
        self.toolbar.pack(fill='x')

        self.root.mainloop()

    def __init__frame_info(self):
        self.frame_info = tkinter.Frame(self.frame)
        self.frame_info.columnconfigure(5, weight=1000)
        
        self.car_name_var = tkinter.StringVar(value='')
        self.peak_power_var = tkinter.DoubleVar(value=0)
        self.peak_power_rpm_var = tkinter.IntVar(value=0)
        self.peak_torque_var = tkinter.DoubleVar(value=0)
        self.peak_torque_rpm_var = tkinter.IntVar(value=0)
        self.revlimit_var = tkinter.DoubleVar(value=0.0)
        self.drag_var = tkinter.DoubleVar(value=0.0)
        self.drag_wheel_var = tkinter.DoubleVar(value=0.0)
        self.top_speed_var = tkinter.DoubleVar(value=0.0)
        self.true_top_speed_var = tkinter.DoubleVar(value=0.0)
        self.true_top_speed_ratio_var = tkinter.StringVar(value=0.0)
        self.drivetrain_var = tkinter.StringVar(value='N/A')
        self.wheelsize_front_var = tkinter.DoubleVar(value=0.0)
        self.wheelsize_rear_var = tkinter.DoubleVar(value=0.0)
        self.shiftdelay_var = tkinter.DoubleVar(value=0.0)
        table = [self.car_name_var, 
                 ['Peak power', self.peak_power_var, 'kW @', self.peak_power_rpm_var, 'rpm'], 
                 ['Peak torque', self.peak_torque_var, 'Nm @', self.peak_torque_rpm_var, 'rpm'],
                 ['Revlimit', self.revlimit_var, ''],
                 ['Drag value', self.drag_var, '(in C*100*v*v)'],
                 ['Wheel drag value', self.drag_wheel_var, '(C*100*v*v/wheelsize)'],
                 ['Top speed', self.top_speed_var, 'km/h'],
                 ['\'True\' top speed', self.true_top_speed_var, 'km/h @', self.true_top_speed_ratio_var, 'ratio'],
                 ['Drivetrain', self.drivetrain_var, ''],
                 ['Wheel radius', self.wheelsize_front_var, 'front', self.wheelsize_rear_var, 'rear (cm)'],
                 ['Shift duration', self.shiftdelay_var, 'seconds']                 
            ]
        
        tkinter.Label(self.frame_info, textvariable=table[0]).grid(row=0, column=0, columnspan=6)
        for i, row in enumerate(table[1:], start=1):
            tkinter.Label(self.frame_info, text=row[0]).grid(row=i, column=0, sticky=tkinter.E)
            tkinter.Label(self.frame_info, textvariable=row[1]).grid(row=i, column=1)
            if len(row) == 3:
                tkinter.Label(self.frame_info, text=row[2]).grid(row=i, column=2, columnspan=3, sticky=tkinter.W)
            else:
                tkinter.Label(self.frame_info, text=row[2]).grid(row=i, column=2, sticky=tkinter.W)
                tkinter.Label(self.frame_info, textvariable=row[3]).grid(row=i, column=3)
                tkinter.Label(self.frame_info, text=row[4]).grid(row=i, column=4, sticky=tkinter.W)   

        self.frame_info.place(relx=0, rely=0.65, anchor=tkinter.W)

    def carname_changed(self, event=None):
        self.fig.clf()
        carname = self.combobox.get()
        filename = self.carlist[carname]
        trace = Trace(fromfile=True, filename=filename)

        #reduce point count by 75% for performance reasons
        last = trace.array[-1]
        start = trace.array[:Trace.REMOVE_FROM_START]
        trace.array = start + trace.array[Trace.REMOVE_FROM_START:-1:4] + [last]
        trace.finish()


        self.gearing = Gearing(trace, self.fig, title=carname)
        self.drag = DragDerivation(trace=None, filename=filename)

        self.drag.draw_torquelosttodrag(ax=self.gearing.ax, step_kmh=Gearing.STEP_KMH, **self.drag.__dict__)
        
        self.car_name_var.set(self.combobox.get())
        peak_power_index = np.argmax(self.drag.power)
        self.peak_power_var.set(round(max(self.drag.power), 1))
        self.peak_power_rpm_var.set(int(self.drag.rpm[peak_power_index]))
        peak_torque_index = np.argmax(self.drag.torque)
        self.peak_torque_var.set(round(max(self.drag.torque), 1))
        self.peak_torque_rpm_var.set(int(self.drag.rpm[peak_torque_index]))
     #  self.revlimit_var.set(int(25*round(self.drag.rpm[-1]/25, 0))) #round to nearest 25
        self.revlimit_var.set(math.ceil(self.drag.rpm[-1]))
        self.drivetrain_var.set(trace.carinfo.get('drivetrain_type', 'N/A'))
        self.drag_var.set(round(100*self.drag.C, 4))
        self.wheelsize_front = float(trace.carinfo.get('wheelsize_front', 0))
        self.wheelsize_rear = float(trace.carinfo.get('wheelsize_rear', 0))        
        self.wheelsize_front_var.set(self.wheelsize_front)
        self.wheelsize_rear_var.set(self.wheelsize_rear)
        
        drag_wheel = 'N/A'
        if self.drivetrain_var.get() == 'FWD':
            drag_wheel = round(100*100*self.drag.C/self.wheelsize_front, 4)
        elif self.drivetrain_var.get() == 'RWD':
            drag_wheel = round(10000*self.drag.C/self.wheelsize_rear, 4)
        elif self.drivetrain_var.get() == 'AWD':
            drag_wheel = round(10000*self.drag.C/(0.4*self.wheelsize_front + 0.6*self.wheelsize_rear), 4)
        self.drag_wheel_var.set(drag_wheel)
        self.top_speed_var.set(round(self.drag.top_speed_by_drag(**self.drag.__dict__), 1))

        gear_ratio, top_speed = self.drag.optimal_final_gear_ratio(**self.drag.__dict__)
        self.true_top_speed_var.set(round(top_speed, 1))
        self.true_top_speed_ratio_var.set(round(gear_ratio, 3))

        shift_delay = trace.carinfo.get('shiftdelay', 0)
        shift_delay = f"±{round(shift_delay/60, 2)}" if shift_delay != 0 else 'N/A'
        self.shiftdelay_var.set(shift_delay)

    #filename structure:
    def generate_carlist(self):
        self.carlist = {}
        for entry in os.scandir(Window.TRACE_DIR):
            filename = entry.name
            ordinal = int(filename.split('_')[1][3:])
            pi = int(filename.split('_')[2][2:-5])

            data = CarData.getinfo(ordinal)
            if data is not None:
                carname = f"{data['maker']} {data['model']} ({data['year']}) PI:{pi} {data['group']}"
                self.carlist[carname] = Window.TRACE_DIR + filename
            else:
                print(f'ordinal {ordinal} NOT FOUND')

class Gearing ():
    STEP_KMH = 25
    FINALRATIO_MIN = 2.2
    FINALRATIO_MAX = 6.1
    GEARRATIO_MIN = 0.48
    GEARRATIO_MAX = 6.00
    RATIO_STEP = 0.01
    
    PERCENTAGELOST_MAX = -30 #used for 'percentage of torque lost vs Peak power torque'
    PERCENTAGELOST_STEP = 5

    def __init__(self, trace, fig=None, final_ratio=1, title=None, car_ordinal=None, car_performance_index=None):
        if fig == None:
            self.fig, (self.ax, self.ax2) = plt.subplots(2,1)
            self.fig.set_size_inches(16, 10)
        else:
            self.fig = fig
            self.ax, self.ax2 = self.fig.subplots(2,1, gridspec_kw={'height_ratios': [2,1]})

        self.ax.grid()
        self.ax.set_ylabel("torque (Nm)")

        self.trace = trace
        self.final_ratio = final_ratio
        self.trace.gears = [g/final_ratio for g in self.trace.gears]

        #sort rpm and torque to be monotonically increasing on rpm
        rpm, torque = zip(*sorted(zip(self.trace.rpm, self.trace.torque)))
        self.trace.rpm = np.array(rpm)
        self.trace.torque = np.array(torque)

        self.graphs = []
        for i, ratio in enumerate(self.trace.gears):
            self.graphs.append(Gear(i, trace, self.ax, self.update, final_ratio))

        #1 km/h per x rpm, scaled to final ratio
        val = (statistics.median([(a/b) for (a, b) in zip(self.trace.rpm, self.trace.speed)]) /
               (self.graphs[self.trace.gear_collected-1].ratio*self.final_ratio))

        valstep = Gearing.STEP_KMH*val

        self.rpmmax = math.ceil(self.trace.rpm[-1]/(self.graphs[-1].ratio*self.final_ratio)/valstep)*valstep
        xticks = np.arange(0,self.rpmmax+valstep,valstep)

        ymax = max(self.trace.torque*self.graphs[0].ratio*self.final_ratio)*1.01

        self.ax.set_ylim(0, ymax)
        self.ax.set_xlim(0, self.rpmmax)
        self.ax.set_xticks(xticks)
        self.ax.set_xlabel("speed (km/h)")
        self.ax.set_xticklabels([math.ceil(x/val) for x in xticks])

        self.ax2.xaxis.tick_top()
        self.ax2.set_xlim(0, self.rpmmax)
        self.ax2.set_xticks(xticks)
        self.ax2.set_xticklabels([])
        yticks = list(range(Gearing.PERCENTAGELOST_MAX, 1, Gearing.PERCENTAGELOST_STEP))
        self.ax2.set_yticks(yticks)
        self.ax2.set_yticklabels([f'{y}%' for y in yticks])

        # self.ax_top = self.ax.secondary_xaxis("top")
        # self.ax_top.set_xlabel("speed (km/h)")
        # self.ax_top.set_xticks(xticks)
        # self.ax_top.set_xticklabels()
        # self.ax_top.set_xticklabels([])

        if title is None:
            if car_ordinal is not None:
                data = CarData.getinfo(car_ordinal)
                title = f"{data['maker']} {data['model']} ({data['year']}) PI:{car_performance_index} {data['group']}"
            else:
                title = ''
                print("we missing a title")

        self.ax.set_title(title)
        self.fig.tight_layout()

        self.__init__power_contour()
        self.__init__sliders()
        self.__init__difference()
        self.ax.legend()

    # def find_intersections(self):
    #     self.data = [graph.get_points() for graph in self.graphs]
    #   #  data = [(x, y-self.power_contour(x)) for x,y in data]
    #     intersections = [intersect.intersection(x1, y1, x2, y2) for (x1,y1), (x2, y2) in zip(self.data[:-1], self.data[1:])]
    #     ratios = [graph.ratio*self.final_ratio for graph in self.graphs]
    #     intersections = [x*r for (x,y),r in zip(intersections, ratios)]
    #     #print(intersections)
    #     return intersections

    def get_difference(self):
        X = 0
        data = [graph.get_points() for graph in self.graphs]
        intersections = [intersect.intersection(x1, y1, x2, y2)[X] for (x1,y1), (x2, y2) in zip(data[:-1], data[1:])]
        intersections = [i[0] if len(i) > 0 else x[-1] for i, (x,y) in zip(intersections, data)]

        min_rpm = data[0][X][0] #initial rpm of first gear
        max_rpm = data[-1][X][-1] #final rpm of final gear
        intersections = [min_rpm] + intersections + [max_rpm]
        x_array, y_array = [], []
        for start, end, (x,y) in zip(intersections[:-1], intersections[1:], data):
            x_array.extend([rpm for rpm in x if rpm >= start and rpm <= end])
            y_array.extend([100*(torque - self.power_contour(rpm)) / self.power_contour(rpm)
                                for rpm, torque in zip(x,y) if rpm >= start and rpm <= end])
        return (x_array, y_array)

    def redraw_difference(self):
        x_array, y_array = self.get_difference()

        self.fillplot.remove()
        self.fillplot = self.ax2.fill_between(x_array, y_array, color='b')
        #    self.diffplot.remove()
        #    self.diffplot, = self.ax2.plot(x_array, y_array, 'b')

    def __init__difference(self):
        x_array, y_array = self.get_difference()
        #     self.diffplot, = self.ax2.plot(x_array, y_array, 'b')
        self.fillplot = self.ax2.fill_between(x_array, y_array, color='b')

        xmin, xmax = self.ax2.get_xlim()
        self.ax2.set_xlim(0, xmax)
        self.ax2.set_ylim(Gearing.PERCENTAGELOST_MAX, 0)
        self.ax2.set_ylabel("percentage of torque lost vs Peak power torque")
        self.ax2.grid()

    def __init__power_contour(self):
        i = self.trace.power.argmax()
        peak_power_torque = self.trace.torque[i]
        peak_power_rpm = self.trace.rpm[i]

        self.power_contour = lambda rpm: peak_power_torque*peak_power_rpm/rpm
        rpm_max = int(2*self.trace.rpm[-1])
        self.ax.plot(self.power_contour(range(1, rpm_max)), label='Peak power torque')

    def slider_limits(self):
        if self.final_ratio == 1:
            final_slider_settings = {'valmin': Gearing.FINALRATIO_MIN / Gearing.FINALRATIO_MAX,
                                     'valmax': Gearing.FINALRATIO_MAX / Gearing.FINALRATIO_MIN}
            gear_slider_settings = {'valmin': Gearing.FINALRATIO_MIN * Gearing.GEARRATIO_MIN,
                                    'valmax': Gearing.FINALRATIO_MAX * Gearing.GEARRATIO_MAX}
        else:
            final_slider_settings = {'valmin': Gearing.FINALRATIO_MIN,
                                     'valmax': Gearing.FINALRATIO_MAX}
            gear_slider_settings = {'valmin': Gearing.GEARRATIO_MIN,
                                    'valmax': Gearing.GEARRATIO_MAX}

        return (final_slider_settings, gear_slider_settings)

    def __init__sliders(self):
        # create space for sliders
        self.fig.subplots_adjust(left=0.35)

        final_slider_limit, gear_slider_limit = self.slider_limits()

        #final gear slider
        self.final_gear_ax = self.fig.add_axes([0.06, 0.90, 0.2, 0.03])
        self.final_gear_slider = Slider(
            ax=self.final_gear_ax,
            label='Final gear',
            valmin=final_slider_limit['valmin'],
            closedmin=False,
            valmax=final_slider_limit['valmax'],
            valinit=self.final_ratio,
            valstep = Gearing.RATIO_STEP
        )
        self.final_gear_slider.on_changed(self.update_final_ratio)

        for graph, ratio in zip(self.graphs, self.trace.gears):
            ax = self.fig.add_axes([0.06, 0.87-0.03*graph.gear, 0.2, 0.03])
            slider = Slider(
                ax=ax,
                label=f'gear {graph.gear+1}',
                valmin=gear_slider_limit['valmin'],
                closedmin=False,
                valmax=gear_slider_limit['valmax'],
                valinit=ratio,
                valstep = Gearing.RATIO_STEP
            )
            graph.add_slider(ax, slider)
            # register the update function with each slider
            graph.slider.on_changed(graph.update)

        #connect sliders: the ratio per slider must be between previous and next gear's ratios
        prev_graph = None
        for a, next_graph in zip(self.graphs, self.graphs[1:]+[None]):
            a.slider.slidermax = prev_graph.slider if prev_graph is not None else None
            a.slider.slidermin = next_graph.slider if next_graph is not None else None
            prev_graph = a

        # Create a `matplotlib.widgzets.Button` to reset the sliders to initial values.
        self.ax_reset = self.fig.add_axes([0.08, 0.54, 0.1, 0.04]) #0.72
        self.button = Button(self.ax_reset, 'Reset', hovercolor='0.975')

        def reset(event):
            self.final_gear_slider.reset()
            for graph in self.graphs:
                graph.slider.reset()
        self.button.on_clicked(reset)

    def update_final_ratio(self, value):
        self.final_ratio = value
        for graph in self.graphs:
            graph.update_final_ratio(value)
        self.redraw_difference()

    def update(self, value):
        self.redraw_difference()

    def run(self):
        pass

if __name__ == "__main__":
    main()
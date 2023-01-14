# -*- coding: utf-8 -*-
"""
Created on Fri Oct 28 18:48:33 2022

@author: RTB
"""

import numpy as np
import math
import statistics
import matplotlib as mpt
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, RangeSlider, Button, CheckButtons
import intersect

from dragderivation import Trace, DragDerivation
from guicarinfo import CarData

'''
TODO:
    - add awd slider for center diff (current assumption is 60%)
    - override slider to add ability to enter ratio
    - add information on shifts
    - add duration for gear at full throttle and no traction issues
    - investigate torque output during a shift
    - split matplotlib drawings into separate canvases
    - maybe replace matplotlib slider with tkinter slider
    - add dump to excel file for all variables

moving the matplotlib sliders into their own canvas resulted in the main canvas
not updating. May be due to a lack of an update call.
'''

def main ():
    global window #trace, gearing, car_ordinal, car_performance_index
    #globals are used for debugging

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
    


import os
import tkinter
import tkinter.ttk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
# suppress matplotlib warning while running in thread
import warnings
warnings.filterwarnings("ignore", category=UserWarning)

SEPARATE_SLIDERS = False

class Window ():
    width = 1500
    height = 1000

    graph_width = 1000
    graph_height = 1000
    
    slider_height = 600

    DEFAULTCAR = 'Acura NSX (2017) PI:831 MODERN SUPERCARS'
    TRACE_DIR = 'traces/'

    def __init__(self):
        self.root = tkinter.Tk()
    #    self.root.tk.call('tk', 'scaling', 1.5) #Spyder console fix for DPI too low
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
        self.fig = Figure(figsize=(Window.width*px, (Window.height-72)*px), dpi=100)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.frame)
        self.canvas.draw() #should be called every update, doesn't seem to be required at all?
        self.fig_slider=None
        self.toolbar = NavigationToolbar2Tk(self.canvas, self.root, pack_toolbar=False)
        self.toolbar.update()

        self.__init__frame_info()

        self.carname_changed()

        self.frame.pack(fill='both', expand=True)
        self.combobox.pack()
        if SEPARATE_SLIDERS:
            self.canvas_slider.get_tk_widget().pack(side='left', anchor=tkinter.N)#fill='both', expand=True)#, anchor=tkinter.W)
        self.canvas.get_tk_widget().pack(side='right')#fill='both', expand=True)#, anchor=tkinter.W)
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
                 ['Peak power:', self.peak_power_var, 'kW @', self.peak_power_rpm_var, 'rpm'], 
                 ['Peak torque:', self.peak_torque_var, 'Nm @', self.peak_torque_rpm_var, 'rpm'],
                 ['Revlimit:', self.revlimit_var, ''],
                 ['Drag value:', self.drag_var, '(in C*100*v*v)'],
                 ['Wheel drag value:', self.drag_wheel_var, '(C*100*v*v/wheelsize)'],
                 ['Top speed:', self.top_speed_var, 'km/h'],
                 ['\'True\' top speed:', self.true_top_speed_var, 'km/h @', self.true_top_speed_ratio_var, 'ratio'],
                 ['Drivetrain:', self.drivetrain_var, ''],
                 ['Wheel radius:', self.wheelsize_front_var, 'front', self.wheelsize_rear_var, 'rear (cm)'],
                 ['Shift duration:', self.shiftdelay_var, 'seconds']                 
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

        self.frame_info.place(relx=0, rely=0.75, anchor=tkinter.W)

    def carname_changed(self, event=None):
        self.fig.clf()
        carname = self.combobox.get()
        filename = self.carlist[carname]
        trace = Trace(fromfile=True, filename=filename)

        #reduce point count to roughly 125-150 for performance reasons
        decimator = int(len(trace.array) / 125)
        last = trace.array[-1]
        start = trace.array[:Trace.REMOVE_FROM_START]
        trace.array = start + trace.array[Trace.REMOVE_FROM_START:-1:decimator] + [last]
        trace.finish()

        final_ratio = Sliders.average_final_ratio(trace.gears)

        self.gearing = Gearing(trace, self.fig, final_ratio=final_ratio, title=carname, fig_slider=self.fig_slider)
        
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
        shift_delay = f"±{shift_delay/60:.3f}" if shift_delay != 0 else 'N/A'
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
        
        #force add legend to axis due to extra legend being added later
        #see https://matplotlib.org/stable/tutorials/intermediate/legend_guide.html
        self.legend = self.ax.legend()
        self.ax.add_artist(self.legend)
        
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
        
        self.shiftrpm = ShiftRPM(self.fig, self.ax, self.gears, self.legend)
        
        self.differencegraph = DifferenceGraph(ax2, self.gears, self.power_contour, 
                                               self.rpmperkmh, self.xmax, self.xticks)
        self.integral_text = self.fig.text(0.06, 0.44, "Transmission efficiency: 100% in range")
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
       self.integral_text.set_text(f"Transmission efficiency: {percentage:5.1f}% in range")

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
        self.print_integral()
        self.shiftrpm.redraw()
        
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
    ypixels = 1000-72 #see Window for these sizes

    axes = {'final_gear':            [0.05, 0.90,          0.2, 0.03],
            'gears':       lambda g: [0.05, 0.87-0.035*g,  0.2, 0.03],
            'rel_ratios':  lambda g: [0.28, 0.8625-0.035*g],
            'reset':                 [0.08, 0.51,          0.2, 0.03],
            'rpmlimit':              [0.05, 0.48,          0.2, 0.03],
            'integral':              [0.05, 0.45,          0.2, 0.03]
            }

    def __init__(self, fig, final_ratio, gears, trace, xmax, rpmperkmh, separate_fig=False):
        if separate_fig:
            Sliders.xmin, Sliders.xmax = 0.2, 1.1
            print("we separate fig")
        else:
            # create space for sliders
            fig.subplots_adjust(left=Sliders.xmax)

        final_slider_limit, gear_slider_limit = self.slider_limits(final_ratio)

        #sliders must have a reference to stay interactive
        self.final_gear_ax = fig.add_axes(Sliders.axes['final_gear'])
        self.final_gear_slider = Slider(
            ax=self.final_gear_ax,
            label='Final gear',
            valmin=final_slider_limit['valmin'],
            closedmin=False,
            valmax=final_slider_limit['valmax'],
            valinit= final_ratio,
            valstep = Sliders.RATIO_STEP,
            valfmt = "%4.2f" #override default to avoid 1.001 as value
        )

        for gear, ratio in zip(gears, trace.gears):
            ax = fig.add_axes(Sliders.axes['gears'](gear.gear))
            slider = Slider(
                ax=ax,
                label=f'gear {gear.gear+1}',
                valmin=gear_slider_limit['valmin'],
                closedmin=False,
                valmax=gear_slider_limit['valmax'],
                valinit=ratio,
                valstep = Sliders.RATIO_STEP
            )
            gear.add_slider(ax, slider) #for resetting
            gear.slider.on_changed(gear.update)

        self.rel_ratios_text = []
        for gear, next_gear in zip(gears[:-1], gears[1:]):
            text = fig.text(*Sliders.axes['rel_ratios'](gear.gear), 
                                          f'{gear.ratio/next_gear.ratio:.2f}')
            self.rel_ratios_text.append(text)

        #connect sliders: the ratio per slider must be between previous and next gear's ratios
        prev_gear = None
        for a, next_gear in zip(gears, gears[1:]+[None]):
            a.slider.slidermax = prev_gear.slider if prev_gear is not None else None
            a.slider.slidermin = next_gear.slider if next_gear is not None else None
            prev_gear = a

        # Create a `matplotlib.widgzets.Button` to reset the sliders to initial values.
        self.ax_reset = fig.add_axes(Sliders.axes['reset']) #0.72
        self.button = Button(self.ax_reset, 'Reset', hovercolor='0.975')
        def reset(event):
            self.final_gear_slider.reset()
            self.rpmlimit_slider.reset()
            for graph in gears:
                graph.slider.reset()
        self.button.on_clicked(reset)
        
        #limit rpm/torque graph to the defined rpm limit (think redline limit for automatic transmission)
        self.rpmlimit_ax = fig.add_axes(Sliders.axes['rpmlimit'])
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
        self.integral_ax = fig.add_axes(Sliders.axes['integral'])
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

    def slider_limits(self, final_ratio):
        if final_ratio == 1:
            final_slider_settings = {'valmin': Sliders.FINALRATIO_MIN / Sliders.FINALRATIO_MAX,
                                     'valmax': Sliders.FINALRATIO_MAX / Sliders.FINALRATIO_MIN}
            gear_slider_settings = {'valmin': Sliders.FINALRATIO_MIN * Sliders.GEARRATIO_MIN,
                                    'valmax': Sliders.FINALRATIO_MAX * Sliders.GEARRATIO_MAX}
        else:
            final_slider_settings = {'valmin': Sliders.FINALRATIO_MIN,
                                     'valmax': Sliders.FINALRATIO_MAX}
            gear_slider_settings = {'valmin': Sliders.GEARRATIO_MIN,
                                    'valmax': Sliders.GEARRATIO_MAX}

        return (final_slider_settings, gear_slider_settings)
        
    @classmethod
    def average_final_ratio(cls, gears):
        upper_limit = min(gears[-1]/Sliders.GEARRATIO_MIN, Sliders.FINALRATIO_MAX) 
        lower_limit = max(gears[0]/Sliders.GEARRATIO_MAX, Sliders.FINALRATIO_MIN)
        return (upper_limit + lower_limit) / 2

class ShiftRPM ():
    checkbutton_ax = [0.01, 0.35, 0.10, 0.14]
    DEFAULTSTATE = True
    
    def __init__(self, fig, ax_graph, gears, legend):
        self.fig = fig
        self.ax_graph = ax_graph
        self.gears = gears
        self.legend = legend
                
        self.ax = fig.add_axes(ShiftRPM.checkbutton_ax) 
        self.ax.axis('off') #remove black border around axis
        self.buttons = CheckButtons(self.ax, ["Display shift RPM lines"], actives=[ShiftRPM.DEFAULTSTATE])
        self.buttons.on_clicked(self.set_visibility)
        
        _, self.ymax = self.ax_graph.get_ylim()
        intersections = self.get_intersections()
        self.vlines = [ax_graph.vlines(i, 0.0, self.ymax, linestyle=':') 
                                   for i, g in zip(intersections, self.gears)]
        
        # for i, g in zip(intersections, self.gears):
        #     g.plot.set_label(f"Gear {g.gear+1}, shift at {i * g.final_ratio * g.ratio:5.0f} rpm")

        self.set_visibility(None)
        
    def set_visibility(self, _):
        toggle = all(self.buttons.get_status()) #assumes single checkbutton
        for vline in self.vlines:
            vline.set_visible(toggle)
        
        self.redraw()
        
        self.fig.canvas.draw_idle()

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
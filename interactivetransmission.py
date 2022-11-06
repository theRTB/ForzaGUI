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

from dragderivation import Trace

#example: stock NSX Acura
car_ordinal = 2352
car_performance_index = 831 
filename = f'traces/trace_ord{car_ordinal}_pi{car_performance_index}.json'

override_gearratio = [] #e.g.: [4.14, 2.67, 1.82, 1.33, 1.00, 0.8]
final_ratio = 1

def main (): 
    global trace, gearing
    trace = Trace(fromfile=True, filename=filename)
    if len(override_gearratio):
        trace.gears = override_gearratio
        trace.gears = [x*final_ratio for x in trace.gears]

    gearing = Gearing(trace, final_ratio=final_ratio)

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

class Gearing ():
    STEP_KMH = 25
    FINALRATIO_MIN = 2.2
    FINALRATIO_MAX = 6.1
    GEARRATIO_MIN = 0.48
    GEARRATIO_MAX = 6.00
    RATIO_STEP = 0.01
    
    def __init__(self, trace, final_ratio=1, title=None):
        self.fig, (self.ax, self.ax2) = plt.subplots(2,1)
        self.fig.set_size_inches(16, 10)
        self.trace = trace
        self.final_ratio = final_ratio
        self.trace.gears = [g/final_ratio for g in self.trace.gears]                
        
        self.graphs = []
        for i, ratio in enumerate(self.trace.gears):
            self.graphs.append(Gear(i, trace, self.ax, self.update, final_ratio))

        self.ax.grid()
       # self.ax.set_xlabel("rpm (final gear)")
        self.ax.set_ylabel("torque (N.m)")

        #1 km/h per x rpm, scaled to final ratio
        val = (statistics.median([(a/b) for (a, b) in zip(self.trace.rpm, self.trace.speed)]) /
               (self.graphs[self.trace.gear_collected-1].ratio*self.final_ratio))
        
        valstep = Gearing.STEP_KMH*val
        
        rpmmax = math.ceil(self.trace.rpm[-1]/(self.graphs[-1].ratio*self.final_ratio)/valstep)*valstep
        xticks = np.arange(0,rpmmax+valstep,valstep)
        
        ymax = max(self.trace.torque*self.graphs[0].ratio*self.final_ratio)
        
        self.ax.set_ylim(0, ymax)
        self.ax.set_xlim(0, rpmmax)    
        self.ax.set_xticks(xticks)
        self.ax.set_xlabel("speed (km/h)")
        self.ax.set_xticklabels([int(x/val) for x in xticks])
        
        self.ax2.xaxis.tick_top()
        self.ax2.set_xlim(0, rpmmax)      
        self.ax2.set_xticks(xticks)  
        self.ax2.set_xticklabels([])
        
        # self.ax_top = self.ax.secondary_xaxis("top")
        # self.ax_top.set_xlabel("speed (km/h)")
        # self.ax_top.set_xticks(xticks)
        # self.ax_top.set_xticklabels()
        # self.ax_top.set_xticklabels([])
        
        self.ax.set_title(title if title is not None else filename)
        self.fig.tight_layout()
        
        self.__init__power_contour()
        self.__init__sliders()        
        self.__init__difference()
        self.ax.legend()

        plt.ion()
        plt.show()

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
            y_array.extend([torque - self.power_contour(rpm) for rpm, torque in zip(x,y) if rpm >= start and rpm <= end])
        return (x_array, y_array)
    
    def redraw_difference(self):
        Y = 1
        x_array, y_array = self.get_difference()
        xmin, xmax = self.ax2.get_xlim()
    #    self.diffplot.remove()
        self.fillplot.remove()
    #    self.diffplot, = self.ax2.plot(x_array, y_array, 'b')
        self.fillplot = self.ax2.fill_between(x_array, y_array, color='b')
        
        self.ax2.set_xlim(0, xmax)
        
        ymin = np.argmax(self.graphs[0].get_points()[Y])        
        self.ax2.set_ylim(y_array[ymin], 0)
        
        self.ax2.set_ylabel("torque lost vs optimal")
        self.ax2.grid()       
        
    def __init__difference(self):
        Y = 1
        x_array, y_array = self.get_difference()
  #      self.diffplot, = self.ax2.plot(x_array, y_array, 'b')
        self.fillplot = self.ax2.fill_between(x_array, y_array, color='b')
        
        ymin = np.argmax(self.graphs[0].get_points()[Y])
        xmin, xmax = self.ax2.get_xlim()
        self.ax2.set_xlim(0, xmax)
        self.ax2.set_ylim(y_array[ymin], 0)
        self.ax2.set_ylabel("torque lost vs optimal")
        self.ax2.grid()
                
    def __init__power_contour(self):
        i = self.trace.power.argmax()
        peak_power_torque = self.trace.torque[i]
        peak_power_rpm = self.trace.rpm[i]   
        
        self.power_contour = lambda rpm: peak_power_torque*peak_power_rpm/rpm
        rpm_max = int(2*self.trace.rpm[-1])
        self.ax.plot(self.power_contour(range(1, rpm_max)), label='Power curve')

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
        plt.subplots_adjust(right=0.7)

        final_slider_limit, gear_slider_limit = self.slider_limits()

        #final gear slider
        self.final_gear_ax = plt.axes([0.76, 0.90, 0.2, 0.03])
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
            ax = plt.axes([0.76, 0.87-0.03*graph.gear, 0.2, 0.03])
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
        self.ax_reset = plt.axes([0.72, 0.54, 0.1, 0.04])
        self.button = Button(self.ax_reset, 'Reset', hovercolor='0.975')

        def reset(event):
            self.final_gear_slider.reset()
            for graph in self.graphs:
                graph.slider.reset()
        self.button.on_clicked(reset)
        
    def update_slider_limits(self):
        ratios = [0] + [gear.ratio for gear in self.graphs] + [36.0/self.final_ratio]
        for ratio_min, ratio_max, graph in zip(ratios[:-1], ratios[1:], self.graphs):
            graph.slider.slidermin = ratio_min
            graph.slider.slidermax = ratio_max

    def update_final_ratio(self, value):
        self.final_ratio = value
        for graph in self.graphs:
            graph.update_final_ratio(value)
        self.redraw_difference()
        
    def update(self, value):
        self.redraw_difference()
#        self.update_slider_limits()
    
    def run(self):
        pass

if __name__ == "__main__":
    main()
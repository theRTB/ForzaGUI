# -*- coding: utf-8 -*-
"""
Created on Tue Jul 26 08:44:40 2022

@author: RTB
"""

import numpy as np
import math
from scipy.signal import butter, lfilter#, freqz
import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, RangeSlider, Button
import csv

sign = lambda x: math.copysign(1, x)

#todo
cols = ['latg', 'longg', 'speed', 'slipFL', 'slipFR', 'slipRL', 'slipRR']

rawdata = {}
#import data from csv
with open('lateralgdata.csv', encoding='ISO-8859-1') as rawcsv:
    csvobject = csv.reader(rawcsv, delimiter='\t')
    names = next(csvobject)
    rawdata = {name:[] for name in names}
    for row in csvobject:
        for name, value in zip(names, row):
            rawdata[name].append(abs(float(value))) 

rawdata['speed'] = [x*3.6 for x in rawdata['speed']]

def butter_lowpass(cutoff, fs, order=5):
    return butter(order, cutoff, fs=fs, btype='low', analog=False)

def butter_lowpass_filter(data, cutoff, fs, order=5):
    b, a = butter_lowpass(cutoff, fs, order=order)
    y = lfilter(b, a, data)
    return y

# Filter requirements.
order = 6  #higher is steeper, see https://stackoverflow.com/questions/63320705/what-are-order-and-critical-frequency-when-creating-a-low-pass-filter-using
fs = 60.0       # sample rate, Hz
cutoff = 5.00  # desired cutoff frequency of the filter, Hz

# Filter the data
data = {}
for col in cols:
    data[col] = butter_lowpass_filter(rawdata[col], cutoff, fs, order)


init_frontslip = (0.5, 2.0)
init_rearslip = (0.5, 2.0)

class LatGGraph ():
    def __init__ (self):
        self.data = data
        self.degree = 2
        
    def update_front(self, front):
        self.update(front, self.rear_slip_slider.val)
        
    def update_rear(self, rear):
        self.update(self.front_slip_slider.val, rear)
        
    # The function to be called anytime a slider's value changes
    def update(self, front, rear):
        frontminval = front[0]
        frontmaxval = front[1]
        rearminval = rear[0]
        rearmaxval = rear[1]
        newdata = [[speed, latg] for speed, latg, slipFL, slipFR, slipRL, slipRR in 
                     zip(self.data['speed'], self.data['latg'], 
                         self.data['slipFL'], self.data['slipFR'], 
                         self.data['slipRL'], self.data['slipRR'])
                     if slipFL >= frontminval and slipFL <= frontmaxval and 
                        slipRL >= rearminval and slipRL <= rearmaxval]
        self.line.set_offsets(newdata)
        
        x = [x[0] for x in sorted(newdata)]
        y = [x[1] for x in sorted(newdata)]
        z = np.polyfit(x, y, self.degree)
        p = np.poly1d(z)
        self.trendline.set_xdata(x)  
        self.trendline.set_ydata(p(x))    
        
        self.fig.canvas.draw_idle()

    def run (self):
        self.fig, self.ax = plt.subplots()
        self.line = plt.scatter('speed', 'latg', data=data, s=1)
        
        #create initial trendline
        x = self.data['speed']
        y = self.data['latg']
        z = np.polyfit(x, y, self.degree)
        p = np.poly1d(z)
        self.trendline, = plt.plot(x, p(x))
        
        self.ax.set_xlabel('Speed [km/h]')
        self.ax.set_xlim(left=0)
        self.ax.set_ylabel('Lateral G [G]')
        self.ax.set_ylim(bottom=0)
        self.ax.grid()
        
        #add filter based on slip
        
        # Make a horizontal slider to control the frequency.
        self.axfrontslip = plt.axes([0.20, 0.15, 0.65, 0.03])
        self.axrearslip = plt.axes([0.20, 0.1, 0.65, 0.03])
        self.front_slip_slider = RangeSlider(
            ax=self.axfrontslip,
            label='Front slip []',
            valmin=0.0,
            valmax=4.0,
            valinit=init_frontslip,
        )
        self.rear_slip_slider = RangeSlider(
            ax=self.axrearslip,
            label='Rear slip []',
            valmin=0.0,
            valmax=4.0,
            valinit=init_rearslip,
        )
        
        #create space for sliders
        plt.subplots_adjust(bottom=0.3)#left=0.25, bottom=0.25)
        
        # register the update function with each slider
        self.front_slip_slider.on_changed(self.update_front)
        self.rear_slip_slider.on_changed(self.update_rear)
        
        # Create a `matplotlib.widgets.Button` to reset the sliders to initial values.
        self.resetax = plt.axes([0.8, 0.025, 0.1, 0.04])
        self.button = Button(self.resetax, 'Reset', hovercolor='0.975')
        
        def reset(event):
            self.front_slip_slider.reset()
            self.rear_slip_slider.reset()
        self.button.on_clicked(reset)
        
        plt.ion()
        plt.show()
        self.update(init_frontslip, init_rearslip)

#track long g relative to speed
#add slider for positive and negative (so accel vs brake)
class LongGGraph ():
    def __init__ (self):
        self.data = data.copy()
        self.degree = 2
        
    # The function to be called anytime a slider's value changes
    def update(self, direction):
        newdata = [[speed, longg] for speed, longg in 
                     zip(self.data['speed'], self.data['longg'])
                     if sign(longg) == direction]
        self.line.set_offsets(newdata)
        
        x = [x[0] for x in sorted(newdata)]
        y = [x[1] for x in sorted(newdata)]
        z = np.polyfit(x, y, self.degree)
        p = np.poly1d(z)
        self.trendline.set_xdata(x)  
        self.trendline.set_ydata(p(x))    
        
        self.fig.canvas.draw_idle()

    def run (self):
        self.fig, self.ax = plt.subplots()
        self.line = plt.scatter('speed', 'longg', data=data, s=1)
        
        #create initial trendline
        x = self.data['speed']
        y = self.data['longg']
        z = np.polyfit(x, y, self.degree)
        p = np.poly1d(z)
        self.trendline, = plt.plot(x, p(x))
        
        self.ax.set_xlabel('Speed [km/h]')
        self.ax.set_xlim(left=0)
        self.ax.set_ylabel('Longitudinal G [G]')
    #    self.ax.set_ylim(bottom=0)
        self.ax.grid()
        
        #add filter based on slip
        
        # Make a horizontal slider to control the frequency.
        self.axdirectionslip = plt.axes([0.20, 0.15, 0.65, 0.03])
    #    self.axrearslip = plt.axes([0.20, 0.1, 0.65, 0.03])
        self.direction_slider = Slider(
            ax=self.axdirectionslip,
            label='Direction []',
            valmin=-1.0,
            valmax=1.0,
            valsteps = [-1, 1],
            valinit=1,
        )
        # self.rear_slip_slider = RangeSlider(
        #     ax=self.axrearslip,
        #     label='Rear slip []',
        #     valmin=0.0,
        #     valmax=4.0,
        #     valinit=init_rearslip,
        # )
        
        #create space for sliders
        plt.subplots_adjust(bottom=0.3)#left=0.25, bottom=0.25)
        
        # register the update function with each slider
        self.direction_slider.on_changed(self.update)
  #      self.rear_slip_slider.on_changed(self.update_rear)
        
        # Create a `matplotlib.widgets.Button` to reset the sliders to initial values.
      #  self.resetax = plt.axes([0.8, 0.025, 0.1, 0.04])
      #  self.button = Button(self.resetax, 'Reset', hovercolor='0.975')
        
  #      def reset(event):
     #       self.front_slip_slider.reset()
     #       self.rear_slip_slider.reset()
    #    self.button.on_clicked(reset)
        
        plt.ion()
        plt.show()
        self.update(1)

graph = LatGGraph()
graph.run()



# def example ():
#     # The parametrized function to be plotted
#     def f(t, amplitude, frequency):
#         return amplitude * np.sin(2 * np.pi * frequency * t)
    
#     t = np.linspace(0, 1, 1000)
    
#     # Define initial parameters
#     init_amplitude = 5
#     init_frequency = 3
    
#     # Create the figure and the line that we will manipulate
#     fig, ax = plt.subplots()
#     line, = plt.plot(t, f(t, init_amplitude, init_frequency), lw=2)
#     ax.set_xlabel('Time [s]')
    
#     # adjust the main plot to make room for the sliders
#     plt.subplots_adjust(left=0.25, bottom=0.25)
    
#     # Make a horizontal slider to control the frequency.
#     axfreq = plt.axes([0.25, 0.1, 0.65, 0.03])
#     freq_slider = Slider(
#         ax=axfreq,
#         label='Frequency [Hz]',
#         valmin=0.1,
#         valmax=30,
#         valinit=init_frequency,
#     )
    
#     # Make a vertically oriented slider to control the amplitude
#     axamp = plt.axes([0.1, 0.25, 0.0225, 0.63])
#     amp_slider = Slider(
#         ax=axamp,
#         label="Amplitude",
#         valmin=0,
#         valmax=10,
#         valinit=init_amplitude,
#         orientation="vertical"
#     )
    
    
#     # The function to be called anytime a slider's value changes
#     def update(val):
#         line.set_ydata(f(t, amp_slider.val, freq_slider.val))
#         fig.canvas.draw_idle()
    
    
#     # register the update function with each slider
#     freq_slider.on_changed(update)
#     amp_slider.on_changed(update)
    
#     # Create a `matplotlib.widgets.Button` to reset the sliders to initial values.
#     resetax = plt.axes([0.8, 0.025, 0.1, 0.04])
#     button = Button(resetax, 'Reset', hovercolor='0.975')
    
    
#     def reset(event):
#         freq_slider.reset()
#         amp_slider.reset()
#     button.on_clicked(reset)
    
#     plt.show()
    
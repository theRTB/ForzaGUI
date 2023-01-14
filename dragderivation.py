# -*- coding: utf-8 -*-
"""
Created on Sun Oct  2 12:56:58 2022

@author: RTB
"""
from scipy import interpolate
#from scipy.misc import derivative
from scipy.optimize import curve_fit
import sys
import statistics
import math
#from scipy.signal import butter, lfilter#, freqz
import matplotlib.pyplot as plt
#import matplotlib.font_manager as font_manager
import numpy as np
#from numpy.polynomial import Polynomial as poly
from pprint import pprint
import json


#steps
#F10 to start updating the GUI
#F9 to toggle collecting gear ratios (this is done through comparing wheel rotation speed and engine rpm)
#disable gear ratio collection after obtaining all the ratios (ignore reverse)
#if necessary: upgrade tire compound because tires must not lose traction during sweep
#head to a drag strip (flat area with tarmac), be in manual
#set gear to one that is affected by drag at the higher rpm values (3rd or 4th normally works)
#be near idle rpm or whatever lowest value where forza doesn't add clutch when full throttle
#press F8, then hold W for 100% throttle
#release W after hitting the rev limit
#click the Sweep button in the GUI to calculate optimal shift rpm

#we need a full acceleration trace:
    # can be derived from an interpolated speed variable differentiated
    # acceleration_z is available, but is a noisy channel, may need smoothing
#we need a full torque graph:
    # derived from the full single gear sweep
#derive scalar by dividing initial torque by initial acceleration
#subtract the acceleration multiplied by the scalar from torque
    # at low speed drag is neglible, thus we assume 100% of torque is used for acceleration
    # realistically, this is 99.x%. 
    # the difference that remains is the effect of drag on the engine torque value
    # there is an initial ramp up to torque that we cannot use and must discard
        #this is done through the CUT variable
    # C is derived from the mean of the last _20_ points, this is a magic constant
    # we brute force an optimal/good cut by looping over it and comparing to a sum of squares of differences
    # given a derived C:
        # we take the minimum value of CUT where:
        # the sum of squares of differences between Cv*v and the array with:
        # the differences between the scaled accel and the torque scaled to gear ratio
        
#scale the torque graph per gear by multiplying speed by the relative ratio
#and dividing the torque by the relative ratio
#if it exists, the intersection of any such torque graphs and the drag penalty is the top speed for that gear

#example: stock NSX Acura
car_ordinal = 2352
car_performance_index = 831 

if len(sys.argv) > 2:
    car_ordinal = sys.argv[1]
    car_performance_index = sys.argv[2]
filename = f'traces/trace_ord{car_ordinal}_pi{car_performance_index}.json'

def main():
    global gears, drag
    drag = DragDerivation(trace=None, filename=filename)
    gears = drag.gears
    
    drag.geardata = DragDerivation.derive_timespeed_all_gears(**drag.__dict__)
    DragDerivation.draw_timespeed_graphs(drag.gears, drag.geardata)
        
    drag.draw_torquegraph(drag.torque, drag.torque_adj, drag.speed, 
                            drag.speed_gradient, drag.gears, drag.gearratio_collected,
                            drag.initial_ratio, drag.C, drag.CUT)
    
    draw_rpm_time(drag, drag.gear_collected, gears, drag.geardata)
    plt.show()
    

def draw_rpm_time(trace, collectedingear, gears, geardata):
    lim = int(len(trace.rpm)/10) #find close fitting ratio for rpm/speed based on the last 10% of the sweep
    rpmspeedratio = np.average(trace.rpm[-lim:] / trace.speed[-lim:])
    gearratio_collected = gears[collectedingear-1]
    
    #data['rpm'] is the drag corrected rpm over time per gear
    fig, ax = plt.subplots(1)
    for data, gearratio in zip(geardata[1:], gears):
        data['rpm'] = data['speed'] * (gearratio / gearratio_collected) * rpmspeedratio
        plt.plot(data['time'], data['rpm'])

class Trace():
    factor_power = 1/1000 #W to KW
    factor_speed = 3.6 #m/s to km/h
    
    REMOVE_FROM_START = 10 #start of a sweep has a rising edge not equivalent to the true engine torque, easier to remove
    DEFAULTFILENAME = "rpmtorqueraw.txt"
    CURRENT_VERSION = 1
    
    def __init__(self, gear_collected=None, gears=[], fromfile=False, filename=None):
        if fromfile:
            if filename is None:
                filename = Trace.DEFAULTFILENAME
            self.readfromfile(filename)
            self.finish()
        else:
            self.array = []
            self.gear_collected = gear_collected
            self.gears = [g for g in gears if g != 0] #strip unused gears
            self.carinfo = {}
            self.version = Trace.CURRENT_VERSION
    
    def add(self, fdp):
        item = (fdp.current_engine_rpm, fdp.torque, fdp.power, fdp.speed, fdp.acceleration_z)
        self.array.append(item)
    
    def add_to_carinfo(self, variables):
        self.carinfo.update(variables)
    
    def finish(self):
        array = self.array[Trace.REMOVE_FROM_START:]
        self.rpm    = np.array([x[0] for x in array])
        self.torque = np.array([x[1] for x in array])
        self.power  = np.array([x[2]*Trace.factor_power for x in array])
        self.speed  = np.array([x[3]*Trace.factor_speed for x in array])
        self.accel  = np.array([x[4] for x in array])

    def readfromfile(self, filename=DEFAULTFILENAME):
        with open(filename) as file:
            raw = json.load(file)
            if type(raw) == list: #old style trace
                self.gear_collected = raw[0]
                self.gears = raw[1]
                self.array = raw[2]
                self.carinfo = {}
                self.version = 0
            elif type(raw) == dict:
                self.gear_collected = raw['gear_collected']
                self.gears = raw['gears']
                self.array = raw['array']
                self.carinfo = raw['carinfo']
                self.version = raw['version']                
        self.finish()

    def writetofile(self, filename=DEFAULTFILENAME):
        filterlist = ['gear_collected', 'gears', 'array', 'carinfo', 'version']
        output = {key:val for key,val in self.__dict__.items() if key in filterlist}
        with open(filename, "w") as file:
            json.dump(output, file)
            
    def legacy_writetofile(self, filename=DEFAULTFILENAME):
        with open(filename, "w") as file:
            json.dump([self.gear_collected, self.gears, self.array], file)

    # def legacy_readfromfile(self, filename=DEFAULTFILENAME):
    #     array = []
    #     with open(filename) as raw:
    #         array = raw.read().split("), (")
        
    #     #manipulate raw input to be readable
    #     array[0]= array[0][2:]
    #     array[-1]= array[0][:-2]
    #     array = array[1:-1]
    #     array = [x.split(', ') for x in array]
        
    #     #convert all data to float
    #     self.array = [[float(p) for p in point] for point in array]

    # def legacy_writetofile(self, filename=DEFAULTFILENAME):
    #     array = list(zip(self.rpm, 
    #                 self.torque, 
    #                 self.power/Trace.factor_power, 
    #                 self.speed/Trace.factor_speed,
    #                 self.accel))
    #     with open(filename, "w") as file:
    #          file.write(str(array))
    
        
#from https://stackoverflow.com/questions/46909373/how-to-find-the-exact-intersection-of-a-curve-as-np-array-with-y-0/46911822#46911822
def find_roots(x,y):
    s = np.abs(np.diff(np.sign(y))).astype(bool)
    return x[:-1][s] + np.diff(x)[s]/(np.abs(y[1:][s]/y[:-1][s])+1)

class DragDerivation():
    MAXCUT = 120+1 #120 frames or 2 seconds
    TIC = 1/60 #seconds
    MAXTIME = 90 #seconds
    MAGIC_CUTOFF = 20
    MODIFIER_ROUNDS = 2 #iterate over modifier in find_winner
    
    def __init__(self, gears=None, final_drive=1, trace=None, gear_collected=None, filename=None):
        #self.gears = [g/final_drive for g in gears]
        #self.final_drive = final_drive
        
        if trace is None:
            #gear_collected cannot be None
            trace = Trace(gear_collected, fromfile=True, filename=filename)
        self.gear_collected = trace.gear_collected
        self.rpm = trace.rpm
        self.torque = trace.torque
        self.power = trace.power
        self.speed = trace.speed
        self.accel = trace.accel
        self.gears = trace.gears
        self.carinfo = trace.carinfo
        
        #self.torque = DragDerivation.convert_to_wheeltorque(self.torque, trace.carinfo)
        
        self.gearratio_collected = self.gears[self.gear_collected-1]
        
        #points are collected at 60hz
        self.time = np.linspace(0, (len(self.speed)-1)/60, len(self.speed))
    
        #accel is gathered separately but is a noisy channel, so we differentiate speed instead
        self.speed_gradient = np.gradient(self.speed, self.time)
    
        #raw data is engine torque, multiply by ratio to get effective torque at the wheel
        #we are not concerned with actual grip levels
        self.torque_adj = self.torque*self.gearratio_collected
    
        winner = self.find_winner(self.torque_adj, self.speed, self.speed_gradient)
        self.points = winner['points']
        self.CUT = winner['CUT']
        self.initial_ratio = winner['initial_ratio']
        self.C = winner['C']
    
    @classmethod
    def convert_to_wheeltorque(cls, torque, carinfo, awd_diff=0.6, *args, **kwargs):
        if carinfo['drivetrain_type'] == 'RWD':
            factor = float(carinfo['wheelsize_rear']) / 100
        if carinfo['drivetrain_type'] == 'FWD':
            factor = float(carinfo['wheelsize_front']) / 100
        if carinfo['drivetrain_type'] == 'AWD':
            factor = (1-awd_diff)*float(carinfo['wheelsize_front'])/100 + awd_diff*float(carinfo['wheelsize_rear'])/100
            
        return torque/factor
    
    #consider replacing speed and speed_gradient with rpm and rpm_gradient
    @classmethod
    def derive_drag_stats(cls, CUT, torque_adj, speed, speed_gradient, ratio_modifier=1, *args, **kwargs):
        initial_ratio = ratio_modifier*torque_adj[CUT]/speed_gradient[CUT]
        
        points = [(s, t - a*initial_ratio) for t, s, a in zip(torque_adj, 
                                                              speed,
                                                              speed_gradient)][CUT:]
        C_all = [ y / (x * x ) for x,y in points]
        C = statistics.mean(C_all[-DragDerivation.MAGIC_CUTOFF:])
        
        lstsq = sum([(y - C*x*x)**2 for x,y in points])
    
        return {'lstsq': lstsq, 'C': C, 'CUT': CUT, 
                      'points': points, 'initial_ratio': initial_ratio}
    
    @classmethod
    def find_winner(cls, torque_adj, speed, speed_gradient, draw_plot=False, *args, **kwargs):
        stats = [DragDerivation.derive_drag_stats(CUT, torque_adj, speed, speed_gradient) 
                                     for CUT in range(DragDerivation.MAXCUT)]
        winner = min(stats, key=lambda x: x['lstsq'])
        if draw_plot: #draw plot of relative positions of each calculation with a specific CUT
            fig, ax = plt.subplots(1)
            pprint(sorted([(x['lstsq'], x['C'], x['CUT']) for x in stats], reverse=True)[-DragDerivation.MAGIC_CUTOFF:])
            ax.scatter([x['lstsq'] for x in stats], [x['C'] for x in stats], s=2)
            for stat in stats:
                ax.annotate(stat['CUT'], (stat['lstsq'], stat['C']))        
        #return winner
    
        #after deriving an initial good guess, modifier finds the impact of drag on the initial ratio
        #we assume this is 0%, but is closer to 0.5-2.5% or whereabouts
        #this method does not necessarily converge, it may oscillate
        for x in range(DragDerivation.MODIFIER_ROUNDS):
            modifier = 1 - (winner['C'] * speed[winner['CUT']] ** 2) / torque_adj[winner['CUT']]
            stats = [DragDerivation.derive_drag_stats(CUT, torque_adj, speed, speed_gradient, modifier) for CUT in range(DragDerivation.MAXCUT)]
            winner = min(stats, key=lambda x: x['lstsq'])
        return winner
    
    @classmethod
    def top_speed_by_drag_of_gearratio(self, torque, speed, gearratio, gearratio_collected, C, do_print=False, *args, **kwargs): 
        speed_ = speed / gearratio * gearratio_collected
        torque_ = torque*gearratio
        array = torque_ - C * speed_ * speed_
        
        z = find_roots(speed_, array)
        if z.size > 0:
            return z[-1] #ignore potential root at head of array due to quick ramp-up of torque
        return 0
        #case 1: torque > Cv^2 for all points on torque curve, 
            #this leads to top speed at revlimit: speed[-1]/gearratio*gears[collectedingear-1]
        #case 2: Cv^2 > torque for all points, no accel possible, top speed is 0
    
    @classmethod
    def top_speed_by_drag_all_gears(cls, torque, speed, gears, gearratio_collected, C, do_print=False, *args, **kwargs):
        returnvalue = []
        gear = len(gears)
        for gear, gearratio in enumerate(gears):
            top_speed = DragDerivation.top_speed_by_drag_of_gearratio(torque, speed, 
                                                                      gearratio, gearratio_collected, C)
            if top_speed > 0:
                geardict = {'gear':gear+1, 'gearratio':gearratio, 'top_speed': top_speed}
                returnvalue.append(geardict) #assume simple scenario of single 
                if (do_print):
                    print(f"gear {geardict['gear']}, ratio {geardict['gearratio']}," 
                          f" top speed: {geardict['top_speed']:.1f} km/h")
        return returnvalue
    
    @classmethod
    def top_speed_by_drag(cls, torque, speed, gears, gearratio_collected, C, *args, **kwargs):
        top_speeds = [x['top_speed'] for x in 
                      DragDerivation.top_speed_by_drag_all_gears(torque, speed, 
                                                               gears, gearratio_collected, C)]
        if len(top_speeds):
            return max(top_speeds)
        return speed[-1]/gears[-1]*gearratio_collected
    
    @classmethod
    def plot_torquevsdrag_atgearratio(cls, torque, speed, gearratio, gearratio_collected, C, *args, **kwargs):
        fig, ax = plt.subplots(1)
        
        ax.plot([s/gearratio*gearratio_collected for s in speed],
                 [t*gearratio for t in torque], label=gearratio)
    
        maxspeed = math.ceil(speed[-1]/gearratio*gearratio_collected)
        torquelost_fitted = [C*x*x for x in range(maxspeed)]
        ax.plot(range(maxspeed), torquelost_fitted, label='torque lost to drag')
    
    @classmethod
    def optimal_final_gear_ratio(cls, torque, speed, gearratio_collected, C, drawgraph=False, *args, **kwargs):
        ratios = np.linspace(0.5, 8.5, 2000+1)
        top_speeds = [DragDerivation.top_speed_by_drag_of_gearratio(torque, speed, gearratio, gearratio_collected, C) for gearratio in ratios]
        
        top_ratio, top_speed = max(zip(ratios, top_speeds), key= lambda x: x[1])
        
        if drawgraph:
            fig, ax = plt.subplots(1)
            ax.plot(ratios, top_speeds)
            ax.set_xlabel('gear ratio')
            ax.set_ylabel('calculated top speed (km/h)')
        
            ymin, ymax = ax.get_ylim()
            ax.vlines(top_ratio, 0, ymax, linestyle=':')
            ax.set_title(f"Highest top speed: {top_speed:.1f} km/h at gear ratio {top_ratio:.4f}")
        
        return top_ratio, top_speed
    
    @classmethod
    def draw_torquelosttodrag(cls, ax, step_kmh, torque_adj, speed, speed_gradient, gears, gearratio_collected, initial_ratio, C, CUT, *args, **kwargs):
        maxspeed = math.ceil(speed[-1]/gears[-1]*gearratio_collected/step_kmh)*step_kmh
        xmin, xmax = ax.get_xlim()
        scalefactor = xmax/maxspeed
        
        CUT = 0 #do not remove unused part of raw data
        line1, = ax.plot(speed[CUT:]*scalefactor, [x - y*initial_ratio for x, y in zip(torque_adj[CUT:], speed_gradient[CUT:])], label='raw data torque lost')    
        maxspeedarray = np.arange(maxspeed)
        torquelost_fitted = [C*x*x for x in maxspeedarray]
        line2, = ax.plot(maxspeedarray*scalefactor, torquelost_fitted, label='torque lost to drag')
        
        first_legend = ax.legend(handles=[line1, line2], loc='lower right', fontsize=8)
        ax.add_artist(first_legend)
        
    @classmethod
    def draw_torquegraph(cls, torque, torque_adj, speed, speed_gradient, gears, gearratio_collected, initial_ratio, C, CUT, *args, **kwargs):
        fig, (ax1, ax2) = plt.subplots(2)
        fig.tight_layout()
        ax1.plot(speed[CUT:], [x - y*initial_ratio for x, y in zip(torque_adj[CUT:], speed_gradient[CUT:])])    
        maxspeed = math.ceil(speed[-1]/gears[-1]*gearratio_collected)
        torquelost_fitted = [C*x*x for x in range(maxspeed)]
        ax1.plot(range(maxspeed), torquelost_fitted, label='torque lost to drag')
        
        for gear in range(len(gears)):
            ax1.plot([s/gears[gear-1]*gearratio_collected for s in speed],
                     [t*gears[gear-1] for t in torque], label=gear+1)
        
    
        top_speeds = DragDerivation.top_speed_by_drag_all_gears(torque, speed, gears, gearratio_collected, C, do_print=True)
        #all memes aside, 488km/h is hard capped top speed in forza on flat ground from engine accel
        vmax = 488
        if len(top_speeds) != 0:
                vmax = max([x['top_speed'] for x in top_speeds])
    
        ax1.set_title(f"modified engine torque versus torque lost to drag, with C:{C:.6f}, CUT: {CUT}, vmax: {int(vmax)} km/h")
        ax1.set_xlabel('speed km/h')
        ax1.set_ylabel('torque')
        
        xmin, xmax = ax1.get_xlim()
        ax1.set_xlim(0, xmax)
        ymin, ymax = ax1.get_ylim()
        ax1.vlines(vmax, 0, ymax, linestyle=':')
        
        ax2.plot([x*torque_adj[CUT]/speed_gradient[CUT] for x in speed_gradient], label='accel scaled to torque')
        ax2.plot(torque_adj[1:-1], label='torque in collected gear')
        xmin, xmax = ax2.get_xlim()
        ax2.set_xlim(0, xmax)
        ymin, ymax = ax2.get_ylim()
        ax2.vlines(CUT, 0, ymax, linestyle=':')
        ax2.set_xlabel('points')
        ax2.legend()
    
    @classmethod
    def find_torque_accel_ratio(cls, torque_adj, speed, speed_gradient, C, drawgraph=False, *args, **kwargs):
        popt, pcov = curve_fit(lambda s, t: interpolate.interp1d(speed, speed_gradient)(s)*t , speed, torque_adj - C*speed*speed)
        t = popt[0]
        
        if drawgraph:
            fig, ax = plt.subplots(1)
            ax.plot(speed, speed_gradient*t)
            ax.plot(speed, torque_adj)
            ax.plot(speed, torque_adj - C*speed*speed)
            
        return t
    
    @classmethod
    def draw_timespeed_graphs(cls, gears, geardata, *args, **kwargs):
        fig, ax = plt.subplots(1)
        fig.tight_layout()
        [ax.plot(geardata[g]['time'], geardata[g]['speed'], label=g) for g in range(1, len(gears)+1)]
    
        ax.set_xlabel('time (s)')
        ax.set_ylabel('speed (km/h)')    
        
    @classmethod
    def derive_timespeed_all_gears(cls, torque, torque_adj, speed, speed_gradient, gears, gearratio_collected, C, drawgraph=False, *args, **kwargs):
        if drawgraph:
            fig, ax = plt.subplots(1)
            fig.tight_layout()
        
        torque_accel_ratio = DragDerivation.find_torque_accel_ratio(torque_adj, speed, speed_gradient, C)
        geararrays = [{}]
        for gear in range(1, len(gears)+1):
            gear_x = speed/gears[gear-1]*gearratio_collected
            gear_y = (torque*gears[gear-1] - C*gear_x*gear_x) / torque_accel_ratio
            gear_interpolate = interpolate.interp1d(gear_x, gear_y, bounds_error=False, fill_value=(gear_y[0], 0))
            
            sum_speed = gear_x[0]
            sum_time = 0
            geardict = {'time':[sum_time], 'speed': [sum_speed]}
            #consider https://www.cs.uu.nl/docs/vakken/mgp/2018-2019/Lecture%205%20-%20Time%20Integration.pdf for improved euler method   
            #TODO: replace gear_x[-1] with min(gear_x[-1] and top speed in gear ratio)
            while sum_speed < gear_x[-1] and sum_time <= DragDerivation.MAXTIME:
                sum_speed +=  gear_interpolate(sum_speed) * DragDerivation.TIC
                sum_time += DragDerivation.TIC
                geardict['time'].append(sum_time)
                geardict['speed'].append(sum_speed)
            
            geardict['time'] = np.array(geardict['time'])
            geardict['speed'] = np.array(geardict['speed'])
            
            geararrays.append(geardict)
            if drawgraph:
                ax.plot(gear_x, gear_y/3.6/9.81, label=gear+1)
        
        if drawgraph:
            ymin, ymax = ax.get_ylim()
            ax.set_ylim(0, ymax)        
            ax.set_xlabel('speed km/h')
            ax.set_ylabel('accel G')
        return geararrays

if __name__ == "__main__":
    main()






        #part of derivetimespeed_all_gears: was used to create full acceleration trace by taking the max accel per gear
        # x = np.linspace(speed[0]/gears[1-1]*gears[collectedingear-1], top_speed_by_drag(C), 10000)
        # y = [max([gearfunc(point) for gearfunc in geararrays]) for point in x]
        # ax.plot(x,y)
        # ax.plot(speed, speed_gradient)



    # top_speeds = top_speed_by_drag_all_gears(C, do_print=True)
    # #all memes aside, 488km/h is hard capped top speed in forza on flat ground from engine accel
    # vmax = max([x['top_speed'] for x in top_speeds] if top_speeds else 488) 

    # ax1.set_title(f"modified engine torque versus torque lost to drag, with C:{C:.6f}, CUT: {CUT}, vmax: {int(vmax)} km/h")
    # ax1.set_xlabel('speed km/h')
    # ax1.set_ylabel('torque')
    
    # top_speeds = top_speed_by_drag_all_gears(C)
    # vmax = max([x['top_speed'] for x in top_speeds] if top_speeds else 488)
    # ymin, ymax = ax1.get_ylim()
    # ax1.vlines(vmax, 0, ymax, linestyle=':')
    
    # ax2.plot([x*torque_adj[CUT]/speed_gradient[CUT] for x in speed_gradient])
    # ax2.plot(torque_adj[1:-1])
    # ymin, ymax = ax2.get_ylim()
    # ax2.vlines(CUT, 0, ymax, linestyle=':')
    # ax2.set_xlabel('points') 


#unused lowpass filter code
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

#consider smoothing accel and using it instead of the differentiated speed variable?
# speed_interpolate = interpolate.interp1d(time, speed)     #this is old, no benefit to using np.gradient or even smoothed accel
# speed_interpolate_deriv = [derivative(speed_interpolate, x, 1e-2) for x in time[1:-1]] #speed_interpolate_deriv is equivalent to accel

# #run backwards over torque per gear over speed vs Cv^2
# def top_speed_by_drag_of_gearratio_old(gearratio, C, do_print=False):    
#     for s,t in zip([s/gearratio*gears[collectedingear-1] for s in reversed(speed)], 
#                    [t*gearratio for t in reversed(torque)]):
#         val = t - C*s*s
#         print(s, t, val)
#         if val >= 0:
#             if (do_print):
#                 print(f"gearratio {gearratio} top speed: {s:.1f} km/h")
#             return s
#     return None

    #old method, does not hold up as the most accurate numbers are ignored (end of array)
    # popt, pcov = curve_fit(lambda t, C: C * t * t, 
    #                        speed[CUT:-1], 
    #                        [x - y*initial_ratio for x, y in zip(torque_adj[CUT:-1], speed_interpolate_deriv)])
    # C = popt[0]
    
# speed_poly = poly.fit(time, speed, 3)
# accel_derived = speed_poly.deriv()/3.6
# accel_derived_derived = accel_derived.deriv()

# y = speed_poly(time)
# z = accel_derived(time)
#plt.plot(speed, accel_derived_derived(time), label='polyfit')
#ax.scatter(speed, accel, label='raw', s=2)
#plt.legend()

# if 0:
#     #plt.plot(speed[CUT:], [x for x in accel_filtered[CUT:]])
#     #plt.plot(speed[CUT:], [x/torque[CUT]*accel_filtered[CUT] for x in torque[CUT:]])
#     #plt.grid()
    
#     # # Fit the function a * np.exp(b * t) + c to x and y
#     popt, pcov = curve_fit(lambda t, a, b, c, d: d * t * t * t + a * t * t + b * t + c, x, y)
#     #popt, pcov = curve_fit(lambda t, c: torque_interpolate(t) - c*t*t , x, y)
    
#     a = popt[0]
#     b = popt[1]
#     c = popt[2]
#     d = popt[3]
    
#     # # Create the fitted curve
#     x_fitted = np.linspace(np.min(x), np.max(x), len(x))
#     y_fitted = d*x_fitted*x_fitted*x_fitted + a*x_fitted*x_fitted + b*x_fitted + c
    
#     print(torque[-1]/torque[CUT]*y_fitted[0] - y_fitted[-1])
    
# # Plot
#ax = plt.axes()
#ax.scatter(x, y, label='Filtered data (5hz lowpass)', s=2)
#ax.scatter(speed[CUT:], accel[CUT:], label='Unfiltered data', s=2)
#ax.plot(x_fitted, y_fitted, 'k', label='Fitted curve')
#ax.plot(speed[CUT:], [x/torque[CUT]*y_fitted[0] for x in torque[CUT:]], label='torque')
#ax.set_title(r'polynom deg 2 fit on accel against torque normalized to initial point of fitted line')
#ax.set_ylabel('accel m/s')
#ax.set_ylim(0, 9)
#ax.legend()
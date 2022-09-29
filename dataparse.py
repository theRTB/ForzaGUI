# -*- coding: utf-8 -*-
"""
Created on Wed Dec 29 18:36:08 2021

@author: RTB
"""

import csv as csv
import numpy as np
import matplotlib.pyplot as plt
import math

def magnitudevector(x,y,z):
    return math.sqrt(x*x+y*y+z*z)


def read_data ():
    with open('data3.csv', 'r') as csvfile:
        csvreader = csv.DictReader(csvfile, delimiter='\t', quotechar='"')
        data =[{x:float(y) for x,y in row.items()} for row in csvreader]    
    return data


data = read_data()

#set useful variables
miny = data[0]['engine_idle_rpm']
maxy = data[0]['engine_max_rpm']


#filter if necessary
data = [d for d in data if d['accel'] > 0 and d['speed'] > 0.1 and d['torque'] >= 0] 


#draw plots
for g in range(1,10):
#    y = [magnitudevector(d['acceleration_x'], d['acceleration_y'], d['acceleration_z'])/9.8 for d in data if d['gear'] == g]
    x = [d['current_engine_rpm'] for d in data if d['gear'] == g]
#    x = [d['timestamp_ms'] for d in data if d['gear'] == g]
#    y = [d['power'] for d in data if d['gear'] == g]
    y = [d['torque'] for d in data if d['gear'] == g]
#    y = [d['speed'] for d in data if d['gear'] == g]
#    y = [d['speed']*3.6/d['current_engine_rpm'] for d in data if d['gear'] == g]
    plt.scatter(x, y, label=g)
plt.legend()
plt.show()


#rev limit


'''
def plot_rpm_speed(forza: CarInfo, ax: axes.Axes = None, row: int = None, col: int = None):
    """plot rpm vs speed

    Args:
        forza (CarInfo): car info
        ax (axes.Axes, optional): figure axes. Defaults to None.
        row (int, optional): position of row. Defaults to None.
        col (int, optional): position of column. Defaults to None.
    """
    color = iter(cm.rainbow(np.linspace(0, 1, len(forza.gear_ratios))))
    for g, item in forza.rpm_torque_map.items():
        raw_records = forza.get_gear_raw_records(g)
        data = np.array([[i['speed'], i['rpm']] for i in raw_records[item['min_rpm_index']:item['max_rpm_index']]])
        data = np.sort(data, 0)
        c = next(color)

        speeds = np.array([item[0] for item in data])
        rpm = np.array([item[1] for item in data])

        ax[row, col].plot(speeds, rpm, label=f'Gear {g} rpm', color=c)
        ax[row, col].set_xlabel('speed (km/h)')
        ax[row, col].set_ylabel('rpm (r/m)')
        ax[row, col].tick_params('y')

    ax[row, col].legend(loc='upper right')
    ax[row, col].set_title('rpm vs Speed')
    ax[row, col].grid(visible=True, color='grey', linestyle='--')
    
    
    Boost is from forced induction. Whether it be a stock car with a turbo or supercharger or you have added them as an upgrade. 
    This isn't a tuna-able item. It should be, especially for drag racing. 
    The boost "guage" or number on telemetry is just to show how much boost or air is being pushed into the engine. 
    Another thing that is all about throttle control. More throttle, more boost, more air being pushed, more power. 
'''
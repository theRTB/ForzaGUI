# -*- coding: utf-8 -*-
"""
Created on Sun Feb  6 16:00:07 2022

@author: RTB
"""

import matplotlib.pyplot as plt
#import matplotlib.font_manager as font_manager
import numpy as np

'''

divide the x values by gear ratio 1, multiply the y  values by gear ratio 1
repeat for gear n
plot in the same space
well actually there are two ways to visualize the same thing, 
up to you which is easier to see
that method would be for values of torque
if you want to instead use values of power, you would 
only divide the x values by the gear ratio


'''

from scipy import interpolate
import statistics
import math

# final_drive = 4.37
# gears = [2.37, 1.91, 1.55, 1.28, 1.08, 0.92, 0.8]
# collectedingear = 4

from dragderivation import Trace
car_ordinal = 3749  #trace_ord3749_pi900
car_performance_index = 900

trace = Trace(fromfile=True, filename=f'trace_ord{car_ordinal}_pi{car_performance_index}.json')

gears = trace.gears
collectedingear = trace.gear_collected
ratios = [gears[x]/gears[x+1] for x in range(len(gears)-1)]


rpm = trace.rpm
torque =  trace.torque
power = trace.power #power in kw
speed = trace.speed #speed in kmh

torque_val = torque[power.argmax()]
rpm_val = rpm[power.argmax()]

ratio_min = rpm[0]

torque_contour = [torque_val*ratio for ratio in np.linspace(0.1, 100, 2000)]
rpm_contour = [rpm_val/ratio*gears[-1] for ratio in np.linspace(0.1, 100, 2000)]


fig, ax = plt.subplots()
#plt.plot(rpm, torque)
ax.plot(rpm, power)


#torque
# graph = [0 for x in range(len(gears)+1)]
# for i,g in enumerate(gears):
#     graph[i+1] = [[x/g for x in rpm], [x*g for x in torque]]
#     plt.plot([x/g for x in rpm], [x*g for x in torque])


#power
#for g in gears:
     #graph[g] = [[x/g for x in rpm], power]
     #plt.plot([x/g for x in rpm], power)
     #plt.vlines([6480/g], .97*max(power), 1.02*max(power))

# gear 1 is rpm power
# gear 2 is rpm*ratio1/ratio2
shiftrpms = []

for ratio in ratios:
    f = interpolate.interp1d(rpm, power)
    g = interpolate.interp1d([x*ratio for x in rpm], power)
    distances = [abs(f(x)-g(x)) for x in range(int(rpm[0]*ratio)+1, int(max(rpm)))]
    index = distances.index(min(distances))
    #print(distances)
    shiftrpm = int(index+rpm[0]*ratio+1)
    shiftrpms.append(shiftrpm)
    print(f"shift rpm {shiftrpm}, drop to {int(shiftrpm/ratio)}, "
          f"drop is {int(shiftrpm*(1.0 - 1.0/ratio))}")

shiftrpms.append(0)
print(len(rpm))
print(len(power))

ratios = [gears[x]/gears[x+1] for x in range(len(gears)-1)]

print(gears)
print(ratios)


#val is the median ratio of rpm and speed scaled to the final ratio
val = statistics.median([(a/b) for (a, b) in zip(rpm, speed)])*gears[-1]/gears[collectedingear-1]

plt.close()
plt.ion()
plt.rcParams["font.family"] = "monospace"
fig, ax = plt.subplots()
fig.set_size_inches(12, 10)
#plt.subplots_adjust(bottom=0.1)
#linerange = max(power) - power[-1]
for i, (g, s) in enumerate(zip(gears, shiftrpms)):
    if i+1 == len(gears):
        label = f'{i+1:>2}  maxspeed {rpm[-1]/val:5.1f}'
    else:
        label = f'{i+1:>2} {s:>9} {gears[-1]*s/(val*g):>10.1f}'
    ax.plot([gears[-1]*x/g for x in rpm], [t*g for t in torque], label=label)  

ymin, ymax = ax.get_ylim()
for g, s in zip(gears, shiftrpms):
    ax.vlines(gears[-1]*s/g, 0, ymax, linestyle=':')
        #ax.vlines(gears[-1]*s/g, power[-1] - vlinerange, ymax, linestyle=':')

#ax.legend(prop=font, title='Gear   shiftrpm   shift at/maxspeed')
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

ax.plot(torque_contour, rpm_contour)

fig.tight_layout()
plt.show()


# #algorithm
# prev = graph[1]
# gear = 1
# for g in graph[2:]:
#     if max(g[1]) < prev[1][-1]:
#         print(f"{gear} to {gear+1}: shift at redline")
#     else:
#         f = interpolate.interp1d(g[0], g[1])
#         distances = [abs(y-f(x)) for x,y in zip(prev[0],prev[1]) if x >= min(g[0]) and x <= max(g[0])]
#         index = distances.index(min(distances))
#         shiftpoint = prev[0][index]*gears[gear-1]
#         print(f"{gear} to {gear+1}: shift at {shiftpoint}")
#     gear += 1
#     prev = g

# plt.grid()
# plt.show()
# plt.tight_layout()

#average power to revlimit

#average power if automatic


# -*- coding: utf-8 -*-
"""
Created on Sun May  7 19:35:24 2023

@author: RTB
"""
import math
import socket
from mttkinter import mtTkinter as tkinter
#import tkinter #replaced with supposed thread safe tkinter variant
#import tkinter.ttk
import winsound
import statistics
from concurrent.futures.thread import ThreadPoolExecutor
from collections import deque
import numpy as np

import ctypes
PROCESS_SYSTEM_DPI_AWARE = 1
PROCESS_PER_MONITOR_DPI_AWARE = 2
ctypes.windll.shcore.SetProcessDpiAwareness(PROCESS_SYSTEM_DPI_AWARE)

from fdp import ForzaDataPacket

#import for ease of debugging
#import matplotlib.pyplot as plt

class constants():
    ip = '127.0.0.1'
    port = 12350
    packet_format = 'fh4'
    sound_file = 'audiocheck.net_sin_1000Hz_-3dBFS_0.1s.wav'
    beep_counter_max = 30 #minimum number of frames between beeps = 0.33ms
    beep_rpm_pct = 0.75 #counter resets below this percentage of beep rpm

    tone_offset = 17
    revlimit_percent = 0.996
    revlimit_frames = 5

    log_full_shiftdata = True
    
    #as rpm ~ speed, and speed ~ tanh, linear regression + extrapolation 
    #overestimates slope and intercept. Keeping the deque short limits this
    linreg_len_min = 15
    linreg_len_max = 20 

    we_beep_max = 30

#full throttle
#max boost all the way
#collect run up to revlimit if possible
#revlimit = positive power to negative power to positive power at full throttle and no gear change
#maybe fine tune revlimit later because it is a multiple of 25 at all times
#a longer run is preferable, but not required


'''
on a per frame basis:
WAIT
wait for throttle to be full

RUN
IF throttle under full: reset and back to WAIT
IF throttle at full and power is negative:
    go to MAYBE_REVLIMIT: we may have hit revlimit, or user has shifted
collect point otherwise

MAYBE_REVLIMIT
IF partial throttle OR gear changed: reset and back to WAIT
IF power is positive and gear unchanged: to TEST
we test for revlimit by enforcing full throttle
if the power was positive, goes negative and then positive again we have hit
the rev limiter.

TEST
test for validity of run
boost must be equal for all points
power at point 0 must be lower or at power at point -1
'''

class RunCollector():
    def __init__(self):
        self.run = []
        self.state = 'WAIT'
        self.prev_rpm = -1
        self.gear_collected = -1

    def update(self, fdp):
        if self.state == 'WAIT':
            if (fdp.accel == 255 and self.prev_rpm < fdp.current_engine_rpm and
                fdp.power > 0):
                self.state = 'RUN'
                self.gear_collected = fdp.gear

        if self.state == 'RUN':
          #  print(f"RUN {fdp.current_engine_rpm}, {fdp.power} {fdp.accel}")
            if fdp.accel < 255:
                # print("RUN RESET")
                self.reset() #back to WAIT
                return
            elif fdp.power <= 0:
                self.state = 'MAYBE_REVLIMIT'
            else:
                self.run.append(fdp)

        if self.state == 'MAYBE_REVLIMIT':
          #  print("MAYBE_REVLIMIT")
            if fdp.accel < 255:
             #   print("MAYBE_REVLIMIT RESET ACCEL NOT FULL")
                self.reset() #back to WAIT
                return
            elif fdp.gear != self.gear_collected:
             #   print("MAYBE_REVLIMIT RESET GEAR CHANGED")
                self.reset() #user messed up
                return
            elif len(self.run) == 1:
             #   print("MAYBE_REVLIMIT RESET LENGTH 1")
                self.reset() #erronous run
                return
            elif fdp.power > 0:
                self.state = 'TEST'

        if self.state == 'TEST':
          #  print("TEST")
            if self.run[0].power > self.run[-1].power:
            #    print("TEST RESET RUN NOT COMPLETE")
                self.reset() #run not clean, started too high rpm
                return
            self.state = 'DONE'
            #TODO: add test for boost:
                #boost at equal power must be equal boost to revlimit boost

        self.prev_rpm = fdp.current_engine_rpm

    def run_completed(self):
        return self.state == 'DONE'

    def get_run(self):
        return self.run

    def reset(self):
        self.run = []
        self.state = 'WAIT'
        self.prev_rpm = -1
        self.gear_collected = -1

class Gear():
    ENTRY_WIDTH = 6
    DEQUE_LEN = 60
    ROW_COUNT = 4

    def __init__(self, root, number, column, starting_row=0):
        self.gear = number
        self.number = tkinter.StringVar(value=f'{number}')
        self.shiftrpm = tkinter.IntVar(value=99999)

        self.ratio = tkinter.DoubleVar(value='0.000')
        self.ratio_deque = deque(maxlen=self.DEQUE_LEN)
        self.state = 'UNUSED'

        self.variance = tkinter.DoubleVar(value='0')

        self.__init__window(root, column, starting_row)

    def __init__window(self, root, column, starting_row):
        self.label = tkinter.Label(root, textvariable=self.number,
                                   width=self.ENTRY_WIDTH)
        self.entry = tkinter.Entry(root, textvariable=self.shiftrpm,
                                   width=self.ENTRY_WIDTH,
                                   justify=tkinter.RIGHT)
        self.entry_ratio = tkinter.Entry(root, textvariable=self.ratio,
                                         width=self.ENTRY_WIDTH,
                                         justify=tkinter.RIGHT)
        self.entry_variance = tkinter.Entry(root, textvariable=self.variance,
                                         width=self.ENTRY_WIDTH,
                                         justify=tkinter.RIGHT)

        self.label.grid(row=starting_row, column=column)
        if self.gear != 10:
            self.entry.grid(row=starting_row+1, column=column)
        self.entry_ratio.grid(row=starting_row+2, column=column)
        self.entry_variance.grid(row=starting_row+3, column=column)

        self.entry_row = starting_row+1
        self.column = column

    def reset(self):
        self.set_shiftrpm(99999)
        self.set_ratio(0)
        self.ratio_deque.clear()
        self.state = 'UNUSED'

        self.variance.set('0')

    def set_shiftrpm(self, val):
        self.shiftrpm.set(int(val))

    def set_ratio(self, val):
        self.ratio.set(f'{val:.3f}')

    def oneshift_handler(self, enabled):
        if enabled:
            if self.gear == 1:
                self.number.set('any')
            elif self.gear == 10:
                self.label.grid_remove()
            else:
                self.label.grid_remove()
                self.entry.grid_remove()
            self.entry_ratio.grid_remove()
            self.entry_variance.grid_remove()
        else:
            if self.gear == 1:
                self.number.set(f'{self.gear}')
            elif self.gear == 10:
                self.label.grid()
            else:
                self.label.grid()
                self.entry.grid()
            self.entry_ratio.grid()
            self.entry_variance.grid()

    def derive_gearratio(self, fdp):
        if self.state == 'UNUSED':
            self.state = 'REACHED'

        if self.state in ['LOCKED', 'CALCULATED']:
            return

        rpm = fdp.current_engine_rpm
        if abs(fdp.speed) < 3 or rpm == 0: #if speed below 3 m/s assume faulty data
            return

        rad = 0
        var_bound = 1e-08
        if fdp.drivetrain_type == 0: #FWD
            rad = (fdp.wheel_rotation_speed_FL +
                   fdp.wheel_rotation_speed_FR) / 2.0
        elif fdp.drivetrain_type == 1: #RWD
            rad = (fdp.wheel_rotation_speed_RL +
                   fdp.wheel_rotation_speed_RR) / 2.0
        else:  #AWD
            rad = (fdp.wheel_rotation_speed_RL +
                   fdp.wheel_rotation_speed_RR) / 2.0
            var_bound = 1e-04 #loosen bound because of higher variance
            # rad = (fdp.wheel_rotation_speed_FL + fdp.wheel_rotation_speed_FR +
            #         fdp.wheel_rotation_speed_RL + fdp.wheel_rotation_speed_RR) / 4.0
        if abs(rad) <= 1e-6:
            return
        if rad < 0: #in the case of reverse
            rad = -rad

        self.ratio_deque.append(2 * math.pi * rpm / (rad * 60))
        if len(self.ratio_deque) < 10:
            return
     #   avg = statistics.mean(self.ratio_deque)
        median = statistics.median(self.ratio_deque)
        var = statistics.variance(self.ratio_deque)#, avg)
        self.variance.set(f'{var:.1e}')
        if var < var_bound and len(self.ratio_deque) == self.DEQUE_LEN:
            if self.state != 'REACHED':
                print(f"gear {self.gear} locked from from state other than REACHED")
            self.state = 'LOCKED'
            print(f'LOCKED {self.gear}')
        self.set_ratio(median)

class ForzaUIBase():
    TITLE = 'ForzaUIBase'
    WIDTH, HEIGHT = 400, 200
    def __init__(self):
        self.threadPool = ThreadPoolExecutor(max_workers=8,
                                             thread_name_prefix="exec")
        # self.listener = Listener(on_press=self.on_press)

        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server_socket.settimeout(1)
        self.server_socket.bind((constants.ip, constants.port))

        self.root = tkinter.Tk()
        self.root.title(self.TITLE)
        self.root.geometry(f"{self.WIDTH}x{self.HEIGHT}")
        self.root.protocol('WM_DELETE_WINDOW', self.close)

        self.active = tkinter.IntVar(value=1)

        # self.__init__window()

    # def __init__vars(self):
    #     print("base __init__vars got called")
    #     pass

    # def __init__window(self):
    #     print("base __init__window got called")
    #     if self.active.get():
    #         self.active_handler()
    #     tkinter.Checkbutton(self.root, text='Active',
    #                         variable=self.active, command=self.active_handler
    #                         ).pack()

    def mainloop(self):
        self.root.mainloop()

    def active_handler(self):
        if self.active.get():
            def starting():
                self.isRunning = True
                self.fdp_loop(self.loop_func)
            self.threadPool.submit(starting)
        else:
            def stopping():
                self.isRunning = False
            self.threadPool.submit(stopping)

    def loop_func(self, fdp):
        pass

    def fdp_loop(self, loop_func=None):
        try:
            while self.isRunning:
                fdp = nextFdp(self.server_socket, constants.packet_format)
                if fdp is None:
                    continue

                if loop_func is not None:
                    loop_func(fdp)
        except BaseException as e:
            print(e)

    def close(self):
        """close program
        """
        self.isRunning = False
        self.threadPool.shutdown(wait=False)
        self.server_socket.close()
     #   self.listener.stop()
        self.root.destroy()

class ForzaBeep(ForzaUIBase):
    TITLE = "ForzaBeep: it beeps, you shift"
    WIDTH, HEIGHT = 745, 205

    MAXGEARS = 10

    MIN_THROTTLE_FOR_BEEP = 255
    REVLIMIT_GUESS = 750  #revlimit = engine_limit - guess
    #distance between revlimit and engine limit varies between 500 and 1250ish

    def __init__(self):
        super().__init__()
        self.__init__vars()
        self.__init__window()
        self.mainloop()

    def __init__vars(self):
        self.isRunning = False
        self.we_beeped = 0
        self.beep_counter = 0
        self.curve = None

        self.rpm = tkinter.IntVar(value=0)
        # self.oneshift = tkinter.IntVar(value=0)
        self.revlimit = tkinter.IntVar(value=-1)
        self.tone_offset = tkinter.IntVar(value=constants.tone_offset)
        self.revlimit_percent = tkinter.DoubleVar(value=constants.revlimit_percent)
        self.revlimit_frames = tkinter.DoubleVar(value=constants.revlimit_frames)

        self.runcollector = RunCollector()
        self.lookahead = Lookahead(constants.linreg_len_min,
                                   constants.linreg_len_max)

        self.shiftdelay_deque = deque(maxlen=120)

        self.car_ordinal = None

    def init_gui_variable(self, name, tkinter_var, row, column):
        tkinter.Label(self.root, text=name).grid(row=row, column=column,
                                                 columnspan=2, sticky='E')
        tkinter.Entry(self.root, textvariable=tkinter_var,
                      width=6, justify=tkinter.RIGHT).grid(row=row, 
                                                           column=column+2)

    def __init__window(self):
        for i, text in enumerate(['Gear', 'RPM', 'Ratio', 'Variance']):
            tkinter.Label(self.root, text=text, width=7).grid(row=i, column=0)

        self.gears = [None] + [Gear(self.root, g, g) for g in range(1, 11)]

        row = Gear.ROW_COUNT

        tkinter.Label(self.root, textvariable=self.rpm, width=5,
                      justify=tkinter.RIGHT, anchor=tkinter.E
                      ).grid(row=row, column=0, sticky=tkinter.W)

        # if self.oneshift.get():
        #     self.oneshift_handler()
        # tkinter.Checkbutton(self.root, text='Single shift RPM',
        #                 variable=self.oneshift, command=self.oneshift_handler
        #             ).grid(row=row, column=2, columnspan=3, sticky=tkinter.W)


        tkinter.Label(self.root, text='Revlimit').grid(row=row, column=2)
        tkinter.Entry(self.root, textvariable=self.revlimit,
                      width=6, justify=tkinter.RIGHT).grid(row=row, column=3)

        resetbutton = tkinter.Button(self.root, text='Reset', borderwidth=3)
        resetbutton.grid(row=row, column=5)
        resetbutton.bind('<Button-1>', self.reset)

        if self.active.get():
            self.active_handler()
        tkinter.Checkbutton(self.root, text='Active',
                            variable=self.active, command=self.active_handler
                            ).grid(row=row, column=7, columnspan=2,
                                   sticky=tkinter.W)
        
        row += 1 #continue on next row
        self.init_gui_variable('Tone offset', self.tone_offset, row, 1)
        self.init_gui_variable('Revlimit %', self.revlimit_percent, row, 4)
        self.init_gui_variable('Revlimit ms', self.revlimit_frames, row, 7)
        # tkinter.Label(self.root, text='Tone offset').grid(row=row, column=1,
        #                                                   columnspan=2)
        # tkinter.Entry(self.root, textvariable=self.tone_offset,
        #               width=6, justify=tkinter.RIGHT).grid(row=row, column=3)

    def reset(self, *args):
        self.runcollector.reset()
        self.lookahead.reset()
        
        self.we_beeped = 0
        self.beep_counter = 0
        self.curve = None
        self.car_ordinal = None
        
        self.rpm.set(0)
        self.revlimit.set(-1)
        
        self.shiftdelay_deque.clear()
        
        for g in self.gears[1:]:
            g.reset()
        
    def oneshift_handler(self):
        for gear in self.gears[1:]:
            gear.oneshift_handler(self.oneshift.get()==1)

    def loop_car_ordinal(self, fdp):
        if self.car_ordinal is None:
            self.car_ordinal = fdp.car_ordinal
        elif self.car_ordinal == 0:
            return
        else:
            self.car_ordinal != fdp.car_ordinal
            self.reset()
            self.car_ordinal = fdp.car_ordinal
            print(f"Ordinal changed to {self.car_ordinal}, resetting!")

    #grab curve if we collected a complete run
    #update curve if we collected a run in a higher gear
    #we can assume that this leads to a more accurate run with a better
    #rev limit defined
    def loop_runcollector(self, fdp):
        self.runcollector.update(fdp)

        if self.runcollector.run_completed():
            if self.curve is None:
            #    print("FIRST RUN DONE!")
                self.curve = self.runcollector.get_run()
                self.revlimit.set(int(self.curve[-1].current_engine_rpm))
            #    print(f'revlimit set: {self.revlimit.get()}')
            else:
                newrun = self.runcollector.get_run()
                if self.curve[0].gear < newrun[0].gear:
                #    print(f"NEW RUN DONE! len {len(newrun)} gear is higher")
                    self.curve = newrun
                    self.revlimit.set(int(self.curve[-1].current_engine_rpm))
                    for g in self.gears[1:]:
                        if g.state == 'CALCULATED':
                            g.state = 'LOCKED'
                            #print(f"Gear {g.gear} reset to LOCKED")
              #      print(f'revlimit set: {self.revlimit.get()}')
                else:
                    pass
               #     print(f"NEW RUN DONE! len {len(newrun)} gear not higher: discarded")
            self.runcollector.reset()

    def loop_calculate_shiftrpms(self):
        if self.curve is not None:
            rpm = [p.current_engine_rpm for p in self.curve]
            power = [p.power for p in self.curve]

            #filter rpm and power
            #sort according to rpm?
            #filter power

            for g1, g2 in zip(self.gears[1:-1], self.gears[2:]):
                if g1.state=='LOCKED' and g2.state in ['LOCKED', 'CALCULATED']:
                    shiftrpm = calculate_shiftrpm(rpm, power,
                                                 g1.ratio.get()/g2.ratio.get())
                    g1.set_shiftrpm(shiftrpm)
                    g1.state = 'CALCULATED'
               #     print(f"gear {g1.gear} shiftrpm set: {shiftrpm}")

    #we assume power is negative between gear change and first frame of shift
    #accel has to be positive at all times, otherwise we don't know for sure
    #where the shift starts
    def loop_test_for_shiftrpm(self, fdp):
        if (len(self.shiftdelay_deque) == 0 or
                self.shiftdelay_deque[0].gear >= fdp.gear or
                self.shiftdelay_deque[0].gear == 0): #case gear reverse
            self.shiftdelay_deque.appendleft(fdp)
            return

        #case gear has gone up
        prev_packet = fdp
        shiftrpm = None
        for packet in self.shiftdelay_deque:
            if packet.accel == 0:
                return
            if prev_packet.power < 0 and packet.power >= 0:
                shiftrpm = packet.current_engine_rpm
                break
            prev_packet = packet
        if shiftrpm is not None:
            optimal = self.gears[fdp.gear-1].shiftrpm.get()
            if constants.log_full_shiftdata:
                print(f"gear {fdp.gear-1}-{fdp.gear}: {shiftrpm:.0f} actual shiftrpm, {optimal} optimal, {shiftrpm - optimal:4.0f} difference")
                print("-"*50)
            self.we_beeped = 0
            self.shiftdelay_deque.clear() #TODO: test if moving this out of the if works better

    def loop_beep(self, fdp, rpm):
        beep_rpm = self.gears[int(fdp.gear)].shiftrpm.get()
        if self.beep_counter <= 0:
            if self.test_for_beep(beep_rpm, self.revlimit.get(), fdp):
                self.beep_counter = constants.beep_counter_max
                self.we_beeped = constants.we_beep_max
                beep()
            elif rpm < math.ceil(beep_rpm*constants.beep_rpm_pct):
                self.beep_counter = 0
        elif self.beep_counter > 0 and rpm < beep_rpm:
            self.beep_counter -= 1

    def loop_func(self, fdp):
        self.loop_car_ordinal(fdp) #reset if car ordinal changes
        
        rpm = fdp.current_engine_rpm
        self.rpm.set(int(rpm))

        gear = int(fdp.gear)
        if gear < 1 or gear > 10:
            return
        if not fdp.is_race_on:
            return

        self.lookahead.add(fdp)

        self.loop_runcollector(fdp)

        self.loop_calculate_shiftrpms()

        if self.revlimit.get() == -1:
            self.revlimit.set(int(fdp.engine_max_rpm - self.REVLIMIT_GUESS))
            print(f'guess revlimit: {self.revlimit.get()}')

        self.loop_test_for_shiftrpm(fdp)

        if self.we_beeped > 0 and constants.log_full_shiftdata:
            print(f'rpm {rpm:.0f} torque {fdp.torque:.1f} slope {self.lookahead.slope:.2f} intercept {self.lookahead.intercept:.2f} count {constants.we_beep_max-self.we_beeped+1}')
            self.we_beeped -= 1
        # if self.oneshift.get():
        #     beep_rpm = self.gears[1].shiftrpm.get()
        # else:
        self.gears[gear].derive_gearratio(fdp)

        self.loop_beep(fdp, rpm)

       # self.last_fdp = fdp

    def torque_ratio_test(self, target_rpm, offset, fdp):
        torque_ratio = 1
        if self.curve and fdp.torque != 0:
            rpms = np.array([p.current_engine_rpm for p in self.curve])
            i = np.argmin(np.abs(rpms - target_rpm))
            target_torque = self.curve[i].torque
            torque_ratio = target_torque / fdp.torque

        return (self.lookahead.test(target_rpm, offset, torque_ratio),
                torque_ratio)

    def test_for_beep(self, shiftrpm, revlimit, fdp):
        # if fdp.accel < self.MIN_THROTTLE_FOR_BEEP:
        #     return False
        tone_offset = self.tone_offset.get()

        from_gear, from_gear_ratio = self.torque_ratio_test(shiftrpm,
                                                            tone_offset, fdp)
        from_gear = from_gear and fdp.accel >= self.MIN_THROTTLE_FOR_BEEP
        
        revlimit_pct, revlimit_pct_ratio = self.torque_ratio_test(
            revlimit*self.revlimit_percent.get(), tone_offset, fdp)
        revlimit_time, revlimit_time_ratio = self.torque_ratio_test(
            revlimit, (tone_offset + self.revlimit_frames.get()), fdp)

        # from_gear = self.lookahead.test(shiftrpm, tone_offset)
        # revlimit_pct = self.lookahead.test(revlimit*self.revlimit_percent.get()
        #                                    , tone_offset)
        # revlimit_time = self.lookahead.test(revlimit, (tone_offset +
        #                                            self.revlimit_frames.get()))

        if from_gear and constants.log_full_shiftdata:
            print(f'beep from_gear: {shiftrpm}, gear {fdp.gear} rpm {fdp.current_engine_rpm:.0f} torque {fdp.torque:.1f} trq_ratio {from_gear_ratio:.2f} slope {self.lookahead.slope:.2f} intercept {self.lookahead.intercept:.2f}')

        if revlimit_pct and constants.log_full_shiftdata:
            print(f'beep revlimit_pct: {revlimit*self.revlimit_percent.get()}, gear {fdp.gear} rpm {fdp.current_engine_rpm:.0f} torque {fdp.torque:.1f} trq_ratio {revlimit_pct_ratio:.2f} slope {self.lookahead.slope:.2f} intercept {self.lookahead.intercept:.2f}')

        if revlimit_time and constants.log_full_shiftdata:
            print(f'beep revlimit_time: {revlimit}, gear {fdp.gear} rpm {fdp.current_engine_rpm:.0f} torque {fdp.torque:.1f} trq_ratio {revlimit_time_ratio:.2f} slope {self.lookahead.slope:.2f} intercept {self.lookahead.intercept:.2f}')

        #print(f'fromgear {from_gear} revlimitpct {revlimit_pct} revlimit_time {revlimit_time} rpm {self.rpm.get()}')
        return from_gear or revlimit_pct or revlimit_time

class Lookahead():
    def __init__(self, minlen, maxlen):
        self.minlen = minlen
        self.deque = deque(maxlen=maxlen)
        self.clear_linreg_vars()

    def add(self, fdp):
        self.deque.append(fdp.current_engine_rpm)
        self.set_linreg_vars()

    def set_linreg_vars(self):
        if len(self.deque) < 2:
            return
        x, y = range(-len(self.deque)+1, 1), self.deque
        self.slope, self.intercept = statistics.linear_regression(x, y)
        if self.slope == 0: #invalid slope
            self.slope = -1

    #x is the frame distance to the most recently added point
    #this has the advantage that the slope is counted from the most recent point
    def distance_to(self, target_rpm):
        if self.slope is None:
            self.set_linreg_vars()
        distance = (target_rpm - self.intercept) / self.slope
        #print(f'target_rpm {target_rpm} slope {slope} intercept {intercept} distance {distance}')
        return distance

    def test(self, target_rpm, lookahead, slope_factor=1):
        if len(self.deque) < 2:
            return
        distance = (target_rpm - self.intercept) / (self.slope * slope_factor)
        return (len(self.deque) > self.minlen and self.slope > 0 and
                0 <= distance <= lookahead)

    def reset(self):
        self.deque.clear()
        self.clear_linreg_vars()

    def clear_linreg_vars(self):
        self.slope, self.intercept = None, None

def beep():
    try:
        winsound.PlaySound(constants.sound_file,
                           winsound.SND_FILENAME | winsound.SND_ASYNC |
                           winsound.SND_NODEFAULT)
    except:
        print("Sound failed to play")

import intersect
def calculate_shiftrpm(rpm, power, ratio):
    rpm = np.array(rpm)
    power = np.array(power)
    X=0
    intersects = intersect.intersection(rpm, power, rpm*ratio, power)[X]
 #   print(intersects)
    shiftrpm = round(intersects[-1],0) if len(intersects) > 0 else rpm[-1]
    print(f"shift rpm {shiftrpm}, drop to {int(shiftrpm/ratio)}, "
          f"drop is {int(shiftrpm*(1.0 - 1.0/ratio))}")

    return shiftrpm

def nextFdp(server_socket: socket, format: str):
    """next fdp

    Args:
        server_socket (socket): socket
        format (str): format

    Returns:
        [ForzaDataPacket]: fdp
    """
    try:
        message, _ = server_socket.recvfrom(1024)
        return ForzaDataPacket(message, packet_format=format)
    except BaseException:
        return None

def main():
    global beep
    beep = ForzaBeep()

if __name__ == "__main__":
    main()

#savitsky-golay
#Keep in mind that in order to have your Savitzky-Golay filter working properly,
#you should always choose an odd number for the window size and the order of
#the polynomial function should always be a number lower than the window size.
from scipy.signal import savgol_filter
def apply_savgol(array):
    window_length = 13
    polyorder = 2
    return savgol_filter(array, window_length, polyorder)

#unused lowpass filter code
#see https://stackoverflow.com/questions/63320705/what-are-order-and-critical-frequency-when-creating-a-low-pass-filter-using
from scipy.signal import butter, lfilter#, freqz
def butter_lowpass(cutoff, fs, order=5):
    return butter(order, cutoff, fs=fs, btype='low', analog=False)

def butter_lowpass_filter(data, cutoff, fs, order=5):
    b, a = butter_lowpass(cutoff, fs, order=order)
    y = lfilter(b, a, data)
    return y

def apply_filter(array):
    # # Filter requirements.
    order = 6  #higher is steeper,
    fs = 60.0       # sample rate, Hz
    cutoff = 5.00  # desired cutoff frequency of the filter, Hz

    array = np.array(array)
    base = array[0]

    return butter_lowpass_filter(array - base, cutoff, fs, order) + base

'''
DONE:
    - determine revlimit
    - gather rpm and power until we have a sweep up to revlimit
    - gather relative ratios between gears
    - calculate intersections
    - extrapolate rpm state in x ms based on current fdp
        - keep deque of ~60 points
        - per point calculate slope
        - extrapolate each point to most recent + 283ms?

    - gui variables
        - Lookahead default 283ms
        - filename?
        - delay until next beep?
        - percentage of revlimit
        - minimum time to revlimit

        well defined revlimit
        revlimit is the lowest rpm value for which:
            - throttle is positive
            - next fdp throttle is positive
            - next fdp power is negative
            - it's not a shift
              - how do we define it's not a shift
            - sequence
              - throttle positive throughout
              - power is positive < revlimit moment, scale to multiple of 25
              - power is negative for x frames
              - power is positive
        well defined rpm/power graph
            - must be maximum boost
            - need a bunch of points 100ish?
            - low range is barely relevant
        well defined gear ratios
         - well defined if variance is low
         - can we manage a low variance on AWD?

    linear regression on 500-750ms of data
    clamp upper end
    suppress beep unless throttle is 100%

    collecting points does not work well
    swap to collecting runs

# class RPMPowerArray ():
#     class Point ():
#         def __init__(self):
#             self.rpm = -1
#             self.power = -1
#             self.boost = -1
#             self.defined = False
#             self.n = 0

#         def assign_from(self, fdp):
#             if not self.defined:
#                 self.rpm = fdp.current_engine_rpm
#                 self.power = fdp.power
#                 self.boost = fdp.boost
#                 self.n = 1
#                 self.defined = True
#             else:
#                 self.rpm = (fdp.current_engine_rpm + self.rpm) / 2
#                 self.power = (fdp.power + self.power) / 2 #bias towards recent points
#                 self.boost = fdp.boost

#         def reset(self):
#             self.__init__()

#         def __repr__(self):
#             return f'{self.rpm:.1f} {self.power/1000:.1f} {self.boost:.2f} {self.defined}'

#     def __init__(self, maxrpm):
#         self.array = [self.Point() for x in range(math.ceil(maxrpm)+1)]
#         self.count = 0

#     def well_defined(self):
#         pass

#     def add(self, fdp):
#         if fdp.accel < 255:
#             return
#         rpm = int(fdp.current_engine_rpm)
#         if fdp.boost < self.boost_lower_bound(rpm):
#             return
#         if fdp.power < 0:
#             return
#         # if fdp.power < self.array[rpm].power:
#         #     return

#         self.array[rpm].assign_from(fdp)
#         self.count += 1
#         print(f'Points added: {self.count}')

#     def boost_lower_bound(self, rpm):
#         rpm = int(rpm)
#         for p in reversed(self.array[:rpm+1]):
#             if not p.defined:
#                 next
#             return p.boost
#         return -15

#     def reset(self):
#         for p in self.array:
#             p.reset()

#     def __repr__(self):
#         return '|'.join([str(p) for p in self.array])
'''
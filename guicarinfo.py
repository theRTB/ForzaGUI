# -*- coding: utf-8 -*-
"""
Created on Sat Jun  4 11:59:00 2022

@author: RTB
"""

#TODO: make a proper tsv out of fh5_cars_kudosprime2.tsv

import tkinter
import tkinter.ttk

import constants

#from cardata import CarData
from interactivetransmission import InfoFrame

class GUICarInfo(InfoFrame):
    def __init__(self, logger, root, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = logger
        self.trace = None
        self.packet = None
        self.CARNAME_FONTSIZE = 16
    
    def set_trace(self, trace):
        self.trace = trace
        self.carname_changed(packet=self.packet, trace=self.trace)

    def set_canvas(self, frame):
        self.frame = tkinter.Frame(frame, border=0, bg=constants.background_color, relief="groove",
                                            highlightthickness=True, highlightcolor=constants.text_color)
        opts = {'bg':constants.background_color, 'fg':constants.text_color, 
                'font': ("Helvetica 11")}#, 'relief':tkinter.SUNKEN}
        super().set_canvas(self.frame, opts)

    def update(self, fdp):
        if fdp.car_ordinal == 0:
            return
        elif self.packet is None:
            self.packet = fdp
            self.carname_changed(packet=fdp, trace=self.trace)
        elif (fdp.car_ordinal != self.packet.car_ordinal and
              fdp.car_performance_index != self.packet.car_performance_index):
            self.trace = None
            self.packet = fdp
            self.carname_changed(packet=fdp)

    def display(self):
        pass
        
    def reset(self):
        self.trace = None
        self.packet = None
        self.reset_vars()
        


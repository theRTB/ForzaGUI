# -*- coding: utf-8 -*-
"""
Created on Sat Jan 29 12:29:19 2022

@author: RTB
"""

import tkinter
import tkinter.ttk
import matplotlib.colors as mcolors
import constants
import helper

class GUITires:
    def __init__(self, tire_canvas=None):
        self.tires = {}
        self.tire_color = mcolors.LinearSegmentedColormap.from_list("", [(0, "green"), (1, "red")])
        self.tire_canvas = tire_canvas

    def update_car_info_tires(self, fdp):
        # FL tire
        slip = abs(fdp.tire_combined_slip_FL) if abs(fdp.tire_combined_slip_FL) < 1 else 1
        color = self.tire_color(slip / 0.8 * 0.5 if slip < 0.8 else (1 - slip) / 0.2 * 0.5 + 0.8)
        self.tire_canvas.itemconfig(self.tires["FL"], fill=helper.rgb(color[0], color[1], color[2]))

        # FR tire
        slip = abs(fdp.tire_combined_slip_FR) if abs(fdp.tire_combined_slip_FR) < 1 else 1
        color = self.tire_color(slip / 0.8 * 0.5 if slip < 0.8 else (1 - slip) / 0.2 * 0.5 + 0.8)
        self.tire_canvas.itemconfig(self.tires["FR"], fill=helper.rgb(color[0], color[1], color[2]))

        # RL tire
        slip = abs(fdp.tire_combined_slip_RL) if abs(fdp.tire_combined_slip_RL) < 1 else 1
        color = self.tire_color(slip / 0.8 * 0.5 if slip < 0.8 else (1 - slip) / 0.2 * 0.5 + 0.8)
        self.tire_canvas.itemconfig(self.tires["RL"], fill=helper.rgb(color[0], color[1], color[2]))

        # RR tire
        slip = abs(fdp.tire_combined_slip_RR) if abs(fdp.tire_combined_slip_RR) < 1 else 1
        color = self.tire_color(slip / 0.8 * 0.5 if slip < 0.8 else (1 - slip) / 0.2 * 0.5 + 0.8)
        self.tire_canvas.itemconfig(self.tires["RR"], fill=helper.rgb(color[0], color[1], color[2]))
        
    def reset_car_info_tires(self):
        # FL tire
        self.tire_canvas.itemconfig(self.tires["FL"], fill=constants.background_color)
    
        # FR tire
        self.tire_canvas.itemconfig(self.tires["FR"], fill=constants.background_color)
    
        # RL tire
        self.tire_canvas.itemconfig(self.tires["RL"], fill=constants.background_color)
    
        # RR tire
        self.tire_canvas.itemconfig(self.tires["RR"], fill=constants.background_color)
        
        
    def set_car_perf_frame_tires(self):
        # place tire information canvas
        self.tire_canvas = tkinter.Canvas(self.car_perf_frame, background=constants.background_color, bd=0,
                                          highlightthickness=False)
        self.tire_canvas.place(relx=constants.tire_canvas_relx, rely=constants.tire_canvas_rely,
                                relwidth=constants.tire_canvas_relwidth, relheight=constants.tire_canvas_relheight,
                                anchor=tkinter.CENTER)
        self.tire_canvas.create_text(self.car_perf_frame.winfo_width() * constants.tire_canvas_relwidth / 2,
                                      self.car_perf_frame.winfo_height() * constants.y_padding_top * 0.5,
                                      text="Tire Information", fill=constants.text_color, font=('Helvetica 15 bold'),
                                      anchor=tkinter.CENTER)
        for pos, info in constants.tires.items():
            self.tires[pos] = self.round_rectangle(self.tire_canvas, self.car_perf_frame.winfo_width() * info[0],
                                                    self.car_perf_frame.winfo_height() * info[1],
                                                    self.car_perf_frame.winfo_width() * info[2],
                                                    self.car_perf_frame.winfo_height() * info[3], radius=info[4],
                                                    fill=constants.background_color, width=2,
                                                    outline=constants.text_color)

    def round_rectangle(self, canvas: tkinter.Canvas, x1, y1, x2, y2, radius=25, **kwargs):
        """draw rectangle with round corner

        Args:
            canvas (tkinter.Canvas): canvas
            x1: top left x coordinate
            y1: top left y coordinate
            x2: bot right x coordinate
            y2: bot right y coordinate
            radius (int, optional): round radius. Defaults to 25.

        Returns:
            rectangle
        """
        points = [x1 + radius, y1,
                  x1 + radius, y1,
                  x2 - radius, y1,
                  x2 - radius, y1,
                  x2, y1,
                  x2, y1 + radius,
                  x2, y1 + radius,
                  x2, y2 - radius,
                  x2, y2 - radius,
                  x2, y2,
                  x2 - radius, y2,
                  x2 - radius, y2,
                  x1 + radius, y2,
                  x1 + radius, y2,
                  x1, y2,
                  x1, y2 - radius,
                  x1, y2 - radius,
                  x1, y1 + radius,
                  x1, y1 + radius,
                  x1, y1]

        return canvas.create_polygon(points, **kwargs, smooth=True)
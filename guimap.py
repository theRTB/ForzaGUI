# -*- coding: utf-8 -*-
"""
Created on Wed Jan 26 16:27:31 2022

@author: RTB
"""

import tkinter
import tkinter.ttk

import constants

class GUIMapDummy:
    def __init__(self, logger):
        pass

    def scale_point(self, x, z):
        pass

    def update(self, fdp):
        pass

    def reset(self):
        pass
        
    def set_canvas (self, frame):
        pass

    def center_map(self):
        pass

    def refresh_map(self):
        pass

class GUIMap:
    def __init__(self, logger):
        self.logger = logger
        
        self.points = []
        self.xz_ratio = 16000.0/11000.0
        self.x_scale = 200.0
        self.x_offset = 10000
        self.z_scale = self.x_scale/self.xz_ratio
        self.z_offset = 6000
        
        self.map_canvas = None

    def scale_point(self, x, z):
        return ((x - self.x_offset)/self.x_scale, 
                (z - self.z_offset)/self.z_scale)

    def update(self, fdp):
        if fdp.is_race_on == 0:
            return
        
        x = fdp.position_x + 10000#(fdp.position_x + 10000)/16000.0
        y = fdp.position_y
        z = -fdp.position_z + 6000#(-fdp.position_z + 6000)/11000.0
             
        #self.update_car_info_pointxyz(x,y,z)
        
        self.points.append((x,y,z))
        
        if len(self.points) == 1:    
            self.x_offset =  self.points[0][0] - self.x_scale/2.0
            self.z_offset =  self.points[0][2] - self.z_scale/2.0
        
        xs, zs = self.scale_point(x,z)
                    
        if xs < 0 or zs < 0 or xs > 1 or zs > 1:
            self.center_map()
            self.logger.info("Map Scale now {:.0f} and {:.0f}".format(self.x_scale, self.z_scale))
            self.refresh_map()
        elif len(self.points) % (60*30) == 0:
            self.logger.info('Redrawing map!')
            self.center_map()
            self.refresh_map()
        else:
            self.map_canvas.create_line(xs*582, zs*400, xs*582+1, zs*400+1, fill='white')      

    def reset(self):
        self.points = []
        self.map_canvas.delete("all")
        
    def set_canvas (self, frame):
        # place map information canvas
        self.map_canvas = tkinter.Canvas(frame, background=constants.background_color, bd=0,
                                          highlightthickness=True, width=582, height=400)
        # self.map_canvas.place(relx=0.6, rely=0.5,
        #                         width=582, height=400,
        #                         anchor=tkinter.CENTER)
        # tkinter.Label(frame, text="Map information", bg=constants.background_color, fg=constants.text_color,
        #               font=('Helvetica 15 bold')).place(relx=0.5, rely=0.0, anchor=tkinter.NW)
                                                                         
        # self.map_canvas.create_line(0,0, 582-1,0, 582-1,400-1, 0,400-1, 0,0, fill='white')

    #todo: optimize so that only new points are checked by saving min/max
    def center_map(self):
        min_x, max_x, min_z, max_z = 16000,0,11000,0
        for p in self.points:
            min_x = p[0] if p[0] < min_x else min_x
            max_x = p[0] if p[0] > max_x else max_x
            min_z = p[2] if p[2] < min_z else min_z
            max_z = p[2] if p[2] > max_z else max_z
        
        new_x_scale = 1.25 * (max_x - min_x)
        new_z_scale = 1.25 * (max_z - min_z)
        
        if new_x_scale / self.x_scale > new_z_scale / self.z_scale:
            self.x_scale = new_x_scale
            self.z_scale = self.x_scale/self.xz_ratio
        else:
            self.z_scale = new_z_scale
            self.x_scale = self.z_scale*self.xz_ratio
        
        self.x_offset = (min_x + max_x) / 2 - self.x_scale/2.0
        self.z_offset = (min_z + max_z) / 2 - self.z_scale/2.0
            

    def refresh_map(self):
        self.map_canvas.delete("all")
        
        points = [self.scale_point(x,z) for x,y,z in self.points]
        points = [[x*582, z*400] for x,z in points]
        
        # newpoints = []
        # prev = points[0]
        # for p in points[1:]:
        #     if prev[0] !=  p[0] or prev[1] != p[1]:
        #         newpoints.append(p)
                
        points = [item for sublist in points for item in sublist]
        self.map_canvas.create_line(*points, fill='white')
        
     #   self.map_canvas.create_line(0,0, 582-1,0, 582-1,400-1, 0,400-1, 0,0, fill='white')


    # def init_pointxyz(self):
    #     self.pointx = tkinter.StringVar()
    #     self.pointx.set("0")
        
    #     self.pointy = tkinter.StringVar()
    #     self.pointy.set("0")
        
    #     self.pointz = tkinter.StringVar()
    #     self.pointz.set("0")

    # def update_car_info_pointxyz(self, x, y, z):
    #     self.pointx.set(f"{str(round(x, 3))}")
    #     self.pointy.set(f"{str(round(y, 3))}")
    #     self.pointz.set(f"{str(round(z, 3))}")

    # def reset_car_info_pointxyz(self):
    #     self.pointx.set("0")
    #     self.pointy.set("0")
    #     self.pointz.set("0")   

    # def set_car_perf_frame_pointxyz(self):
    #     # place Pos x information text
    #     tkinter.Label(self.car_perf_frame, text="Pos x", bg=constants.background_color, fg=constants.text_color,
    #                   font=('Helvetica 15 bold')).place(relx=0.0, rely=0.1, anchor=tkinter.NW)
    #     tkinter.Label(self.car_perf_frame, textvariable=self.pointx, bg=constants.background_color,
    #                   fg=constants.text_color, font=('Helvetica 20 bold italic')).place(relx=0.0, rely=0.2,
    #                                                                                     anchor=tkinter.NW)

    #     # place pos y information test
    #     tkinter.Label(self.car_perf_frame, text="Pos y", bg=constants.background_color, fg=constants.text_color,
    #                   font=('Helvetica 15 bold')).place(relx=0.0, rely=0.3, anchor=tkinter.NW)
    #     tkinter.Label(self.car_perf_frame, textvariable=self.pointy, bg=constants.background_color,
    #                   fg=constants.text_color, font=('Helvetica 20 bold italic')).place(relx=0.0, rely=0.4,
    #                                                                                     anchor=tkinter.NW)
    #     # place pos z information test
    #     tkinter.Label(self.car_perf_frame, text="Pos z", bg=constants.background_color, fg=constants.text_color,
    #                   font=('Helvetica 15 bold')).place(relx=0.0, rely=0.5, anchor=tkinter.NW)
    #     tkinter.Label(self.car_perf_frame, textvariable=self.pointz, bg=constants.background_color,
    #                   fg=constants.text_color, font=('Helvetica 20 bold italic')).place(relx=0.0, rely=0.6,
    #                                                                                     anchor=tkinter.NW)    
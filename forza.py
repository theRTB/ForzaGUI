import os
import socket
import time
from concurrent.futures.thread import ThreadPoolExecutor
from os import listdir
from os.path import isfile, join

from fdp import ForzaDataPacket

import constants
import helper
from logger import Logger


class Forza():
    def __init__(self, threadPool: ThreadPoolExecutor, logger: Logger = None, packet_format='fh4', clutch = False):
        """initialization

        Args:
            threadPool (ThreadPoolExecutor): threadPool
            packet_format (str, optional): packet_format. Defaults to 'fh4'.
            clutch (bool, optional): clutch. Defaults to False.
        """
        super().__init__()

        # === logger ===
        self.logger = (Logger()('Forza5')) if logger is None else logger

        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server_socket.settimeout(1)
        #self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) #Issue spyder console does not allow re-opening of gui.py, port in use. This does not fix as suggested by Googel
        self.server_socket.bind((constants.ip, constants.port))
        self.logger.info('listening on port {}'.format(constants.port))

        self.packet_format = packet_format
        self.isRunning = False
        self.threadPool = threadPool
        self.clutch = clutch

        # # constant
        # self.config_folder = os.path.join(constants.root_path, 'config')

        # # create folders if not existed
        # if not os.path.exists(self.config_folder):
        #     os.makedirs(self.config_folder)

    def test_gear(self, update_car_gui_func=None):
        """collect gear information

        Args:
            update_car_gui_func (optional): callback to update car gui. Defaults to None.
        """
        try:
            self.logger.debug(f'{self.test_gear.__name__} started')
            while self.isRunning:
                fdp = helper.nextFdp(self.server_socket, self.packet_format)
                if fdp is None:
                    continue

                if fdp.is_race_on and fdp.current_engine_rpm > 0:
                    if update_car_gui_func is not None:
                        update_car_gui_func(fdp)
                    info = {
                        'gear': fdp.gear,
                        'rpm': fdp.current_engine_rpm,
                        'time': time.time(),
                        'speed': fdp.speed * 3.6,
                        'clutch': fdp.clutch,
                        'power': fdp.power / 1000.0,
                        'torque': fdp.torque,
                        'car_ordinal':str(fdp.car_ordinal),
                        'speed/rpm': fdp.speed * 3.6 / fdp.current_engine_rpm,
                        'posx': fdp.position_x,
                        'posy': fdp.position_y,
                        'posz': fdp.position_z
                        
                    }
                    self.logger.debug(info)

        except BaseException as e:
            self.logger.exception(e)
        finally:
            self.isRunning = False
            self.logger.debug(f'{self.test_gear.__name__} finished')

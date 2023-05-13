import socket
# import time
from concurrent.futures.thread import ThreadPoolExecutor

from fdp import ForzaDataPacket

import constants
from logger import Logger

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

    def test_gear(self, update_car_gui_func=None):
        """collect gear information

        Args:
            update_car_gui_func (optional): callback to update car gui. Defaults to None.
        """
        try:
            while self.isRunning:
                fdp = nextFdp(self.server_socket, self.packet_format)
                if fdp is None:
                    continue
                    
                if update_car_gui_func is not None:
                    update_car_gui_func(fdp)

        except BaseException as e:
            self.logger.exception(e)

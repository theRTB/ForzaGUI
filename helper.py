import json
import os
import socket
import sys
from socket import socket

from car_info import CarInfo

sys.path.append(r'./forza_motorsport')
import numpy as np
from fdp import ForzaDataPacket
from matplotlib import axes
from matplotlib.pyplot import cm


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

def convert(n: object):
    """variables to json serializable

    Args:
        n (object): object to parse

    Returns:
        serializable value
    """
    if isinstance(n, np.int32) or isinstance(n, np.int64):
        return n.item()

def dump_config(forza: CarInfo):
    """dump config

    Args:
        forza (CarInfo): car info
    """
    try:
        forza.logger.debug(f'{dump_config.__name__} started')
        forza.ordinal = forza.records[0]['car_ordinal']
        config = {
            # === dump data and result ===
            'ordinal': forza.ordinal,
            'minGear': forza.minGear,
            'maxGear': forza.maxGear,
            'gear_ratios': forza.gear_ratios,
            'rpm_torque_map': forza.rpm_torque_map,
            'shift_point': forza.shift_point,
            'records': forza.records,
        }

        with open(os.path.join(forza.config_folder, f'{forza.ordinal}.json'), "w") as f:
            json.dump(config, f, default=convert, indent=4)
    finally:
        forza.logger.debug(f'{dump_config.__name__} ended')

def load_config(forza: CarInfo, path: str):
    """load config as carinfo

    Args:
        forza (CarInfo): car info
        path (str): config path
    """
    try:
        forza.logger.debug(f'{load_config.__name__} started')
        with open(os.path.join(forza.config_folder, path), "r") as f:
            config = json.loads(f.read())

        if 'ordinal' in config:
            forza.ordinal = str(config['ordinal'])

        if 'minGear' in config:
            forza.minGear = config['minGear']

        if 'maxGear' in config:
            forza.maxGear = config['maxGear']

        if 'gear_ratios' in config:
            forza.gear_ratios = {int(key): value for key, value in config['gear_ratios'].items()}

        if 'rpm_torque_map' in config:
            forza.rpm_torque_map = {int(key): value for key, value in config['rpm_torque_map'].items()}

        if 'shift_point' in config:
            forza.shift_point = {int(key): value for key, value in config['shift_point'].items()}

        if 'records' in config:
            forza.records = config['records']
    finally:
        forza.logger.debug(f'{load_config.__name__} ended')

def rgb(r, g, b):
    """generate rbg in hex

    Args:
        r
        g
        b

    Returns:
        rgb in hex
    """
    return "#%s%s%s" % tuple([hex(int(c * 255))[2:].rjust(2, "0") for c in (r, g, b)])

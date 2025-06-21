# Copyright (c) 2023 Reiner Nikulski
# 
# This software is released under the MIT License.
# https://opensource.org/licenses/MIT

import sys
if 'micropython' not in sys.version.lower():
    from typing import List

class RobbySettings:
    """RobbySettings contains all settings, parameters and label texts for the robot."""
    MAX_BALL_FREQUENCY = 1.0
    LABEL_PARAM_BALL_SPEED = 'BallSpeed'
    LABEL_PARAM_TOPSPIN = 'Topspin'
    LABEL_PARAM_SIDESPIN = 'Sidespin'
    LABEL_PARAM_BALL_FREQUENCY = 'BallFrequency'
    #DEFAULT_BALL_FEEDER_CYCLE = [-40, 120, -80] 
    """Number of steps for the stepper motors until a full ball feeding operation has been performed. Waiting time between the shots occurs after the last entry (waiting position).
       Optimal waiting position is when the feeder is just holding back the next ball, i.e. the list items describe these movements:
       0: release the next ball (let drop)
       1: push the ball into the ball driver
       2: prepare the next cycle as far as possible while still holding back the next ball.
    """
    #DEFAULT_BALL_FEEDER_MOUNT_INDEX = 1
    """Mounting the feeder should be done in one of the end positions (for the ease of doing) and after mounting, the machine must perform movements to reach the waiting position (last pos in the feeder cycle).
       The mount index points to the position index from the feeder cycle where the mounting is done. 
    """

    def __init__(self, ballspeed = 1.0, topspin = 0.0, sidespin = 0.0, ballfreq = 0.2) -> None:
        """ballspeed, topspin, sidespin, ballfreq are the initial default values for the shots"""
        self.net_hostname = 'TTRobby'
        self.net_webserver_autostart = True
        self.net_webserver_port = 80
        self.net_start_webserver = True
        self.default_ball_speed = ballspeed
        self.default_topspin = topspin
        self.default_sidespin = sidespin
        self.default_ball_frequency = ballfreq
    
    def __set_ball_speed(self, value: float) -> None:
        if value < 0.0:
            value = 0.0
        self.__default_ball_speed = value

    def __set_topspin(self, value: float) -> None:
        if value > 1.0:
            value = 1.0
        elif value < -1.0:
            value = -1.0
        self.__default_topspin = value

    def __set_sidespin(self, value: float) -> None:
        if value > 1.0:
            value = 1.0
        elif value < -1.0:
            value = -1.0
        self.__default_sidespin = value

    def __set_ball_frequency(self, value: float) -> None:
        if value < 0.0:
            value = 0.0
        # ensure that rotation speed is high enough to keep ball frequency
        self.__default_ball_frequency = min(value, self.MAX_BALL_FREQUENCY)

    def __set_net_hostname(self, value: str) -> None:
        self.__net_hostname = value

    def __set_net_webserver_autostart(self, value: bool) -> None:
        self.__net_webserver_autostart = value

    def __set_net_webserver_port(self, value: int) -> None:
        self.__net_webserver_port = value

    def __set_net_wlan_name(self, value: str) -> None:
        self.__net_wlan_name = value
    def __set_net_wlan_key(self, value: str) -> None:
        self.__net_wlan_key = value

    net_wlan_name = property(lambda self: self.__net_wlan_name, __set_net_wlan_name)
    """name of the wlan to connect to"""
    # net_wlan_key = property(lambda self: self.__net_wlan_key, __set_net_wlan_key)
    # """key for the wlan to connect to"""
    net_webserver_port = property(lambda self: self.__net_webserver_port, __set_net_webserver_port)
    """listening port for the webserver"""
    net_webserver_autostart = property(lambda self: self.__net_webserver_autostart, __set_net_webserver_autostart)
    """start webserver at startup"""
    net_hostname = property(lambda self: self.__net_hostname, __set_net_hostname)
    """hostname for the device"""
    default_ball_speed = property(lambda self: self.__default_ball_speed, __set_ball_speed)
    """ball's forward speed"""
    default_topspin = property(lambda self: self.__default_topspin, __set_topspin)
    """ball's rotation around the horizontal axis: -1=max backspin to +1=max topspin"""
    default_sidespin = property(lambda self: self.__default_sidespin , __set_sidespin)
    """ball's rotation around the vertical axis: -1=max right spin to +1=max. left spin"""
    default_ball_frequency = property(lambda self: self.__default_ball_frequency, __set_ball_frequency)
    """number of balls played per second"""

    def getConfigData(self) -> dict:
        return {
            'hostname': self.net_hostname,
            'net_webserver_autostart': self.net_webserver_autostart,
            'net_webserver_port': self.net_webserver_port,
            'max_ball_frequency': self.MAX_BALL_FREQUENCY,
            'default_topspin': self.default_topspin,
            'default_sidespin': self.default_sidespin,
            'default_ballspeed': self.default_ball_speed,
        }
    def load_from_config(self, config: dict):
        if 'hostname' in config:
            self.net_hostname = str(config['hostname'])
        if 'net_webserver_autostart' in config:
            self.net_webserver_autostart = str(config['net_webserver_autostart']).lower() in ['true', '1', 'y', 'yes']
        if 'net_webserver_port' in config:
            self.net_webserver_port = int(config['net_webserver_port'])
        if 'max_ball_frequency' in config:
            self.MAX_BALL_FREQUENCY = float(config['max_ball_frequency'])
        if 'default_topspin' in config:
            self.default_topspin = float(config['default_topspin'])
        if 'default_sidespin' in config:
            self.default_sidespin = float(config['default_sidespin'])
        if 'default_ballspeed' in config:
            self.default_ball_speed = float(config['default_ballspeed'])

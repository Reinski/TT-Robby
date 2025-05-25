# Copyright (c) 2023 Reiner Nikulski
# 
# This software is released under the MIT License.
# https://opensource.org/licenses/MIT

import BallDriver, RobbySettings

class Shot:
    """Shot defines how the machine must play the ball and with which of its ball drivers (there might be multiple)."""
    def __init__(self, topspin: float, sidespin: float, speed: float, pause: float, h_angle: int, v_angle: int, ball_driver_index: int = 0):
        self.__topspin = topspin
        self.__sidespin = sidespin
        self.__speed = speed
        self.__pause = pause
        self.__horiz_angle = h_angle
        self.__vert_angle = v_angle
        self.__bd_number = ball_driver_index
        self.__motor_settings = None

    def init_for_bd(self, ball_driver: BallDriver.BallDriver, ball_driver_index: int = -1):
        """Initializes the shot for a specific ball driver. The bd must take care to call this method before it actually plays the shot."""
        self.__motor_settings = ball_driver.calc_motor_speeds(self.__speed, self.__topspin, self.__sidespin)
        if ball_driver_index >= 0:
            self.__bd_number = ball_driver_index

    def __set_topspin(self, value: float):
        if value < 0.0:
            self.__topspin = 0.0
        elif value > 1.0:
            self.__topspin = 1.0
        else:
            self.__topspin = value

    def __set_sidespin(self, value: float):
        if value < 0.0:
            self.__sidespin = 0.0
        elif value > 1.0:
            self.__sidespin = 1.0
        else:
            self.__sidespin = value

    def __set_ball_speed(self, value: float):
        if value < 0.0:
            self.__speed = 0.0
        elif value > 1.0:
            self.__speed = 1.0
        else:
            self.__speed = value

    def __set_pause(self, value: float):
        if value < 0.0:
            self.__pause = 0.0
        else:
            self.__speed = value

    BallDriverNumber = property(lambda self: self.__bd_number)
    """Get the balldriver index (technical interface)"""
    MotorSettings = property(lambda self: self.__motor_settings)
    """Get the motor settings (technical interface)"""
    BallSpeed = property(lambda self: self.__ball_speed, __set_ball_speed)
    """ball's forward speed"""
    Topspin = property(lambda self: self.__topspin, __set_topspin)
    """ball's rotation around the horizontal axis: -1=max backspin to +1=max topspin"""
    Sidespin = property(lambda self: self.__sidespin , __set_sidespin)
    """ball's rotation around the vertical axis: -1=max right spin to +1=max. left spin"""
    Pause = property(lambda self: self.__pause, __set_pause)
    """pause time between balls played in seconds"""
    HorizontalAngle = property(lambda self: self.__horiz_angle)
    """horizontal angle in degrees, with 0 being the center"""
    VerticalAngle = property(lambda self: self.__vert_angle)
    """vertical angle in degrees, with positive meaning upward and negative meaning downward"""

    def getConfigData(self) -> dict:
        # Since Shot only contains configuration data, there is no status method.
        return {
            'speed': self.__speed,
            'topspin': self.__topspin,
            'sidespin': self.__sidespin,
            'pause': self.__pause,
            'h_angle': self.__horiz_angle,
            'v_angle': self.__vert_angle,
        }

    @classmethod
    def get_default_shot_from_settings(cls, settings: RobbySettings.RobbySettings) -> Shot:
        return Shot(settings.default_topspin, settings.default_sidespin, settings.default_ball_speed, 1.0/settings.default_ball_frequency, 0, 0)

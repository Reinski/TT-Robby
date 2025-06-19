# Copyright (c) 2023 Reiner Nikulski
# 
# This software is released under the MIT License.
# https://opensource.org/licenses/MIT
import sys
if 'micropython' not in sys.version.lower():
    from typing import List, Union
import math
import time
from DcMotor import DcMotor
from Pca9685 import PCA9685, PIN_SDA, I2C_CHANNEL
from RobbyExceptions import InputDataException

class BallDriver():
    """BallDriver controls the DC motors used to accelerate the ball."""
    # Device dependent parameters
    v_ball_max = 33 # ball's max speed in m/s
    w_h_max = 150 # max topspin rotation in 1/s
    w_v_max = 150 # max sidespin rotation in 1/s
    r_ball = 0.022 # ball radius in m
    # d_wheel0 = 0.05 # wheel diameter in m
    # d_wheel1 = 0.05 # wheel diameter in m
    # d_wheel2 = 0.05 # wheel diameter in m

    def __init__(self, bd_number: int, motor_angles=[0, 180], i2c_channel: int=I2C_CHANNEL, sda_pin: int=PIN_SDA, address: Union[int, None]=0x40, debug: Union[bool, None]=None) -> None:
        """Parameters:
           bd_number: identifier for this ball driver.
           motor_angles: mapping of connected motors (by index) to their orientation (by angle). 0° refers to top, 60° to top left, etc. in the machine's forward axial view.
           sda_pin: GP-pin number on the pico where the motor shield (pca9685) is connected.
           address: I2C address
           debug: Set to True to enable debug output
        """
        if debug is None:
            self.debug = False
        else:
            self.debug = debug
        self.bd_number = bd_number
        self._status = 0 # 0: stopped; 1: active (but motors may be at speed 0!)
        try:
            self.motorDriver = PCA9685(address, self.debug, i2c_channel, sda_pin)
        except OSError as e:
            raise OSError(f"ERROR: BallDriver #{bd_number} could not initialize PCA9685 motor driver on {sda_pin} channel {i2c_channel} (please check the wiring): {e}")
        self.motorDriver.setPWMFreq(50)
        self.motor_angles = [a for a in motor_angles if a is not None]
        self.motors = [DcMotor(self.motorDriver, i_mot, 1, self.debug) for i_mot in range(len(self.motor_angles))]
        self.wheel_diameters = [0.04 for _ in self.motors] # wheel diameters in m
        self.motorSpeeds = [0 for _ in self.motors] # current motor speeds (normalized to 100)

    def calc_motor_speeds(self, v_ball_norm = 1.0, w_h_norm = 0.0, w_v_norm = 0.0) -> List[int]:
        """
        Gets the motor speeds for the specified ball parameters.
        
        Parameters:
        v_ball_norm: ball's translational speed (considered horizontal, normalized to 1=max-speed)
        w_h_norm: horizontal angular speed --> topspin(+)/backspin(-) between -1 and +1
        w_v_norm: vertical angular speed --> sidespin-counterclock(+)/sidespin-clockwise(-) between -1 and +1
        Returns:
        Tuple with the speed setting per motor, unit of % (-100% to +100%)
        """
        if self.debug:
            print(f"calc_motor_speeds({v_ball_norm=}, {w_h_norm=}, {w_v_norm=})")

        v_ball_min = 0.1
        if v_ball_norm == 0:
            return [0 for _ in self.motors]
        elif v_ball_norm > 1.0:
            v_ball_norm = 1.0
        elif v_ball_norm < v_ball_min:
            v_ball_norm = v_ball_min
        if w_h_norm > 1.0:
            w_h_norm = 1.0
        elif w_h_norm < -1.0:
            w_h_norm = -1.0
        if w_v_norm > 1.0:
            w_v_norm = 1.0
        elif w_v_norm < -1.0:
            w_v_norm = -1.0
        
        if len(self.motors) != 2:
            raise NotImplementedError(f"Having {len(self.motors)} motors is currently not supported!")

        # Due to restriction on two motors (up and down), a simplified calculation is possible
        # and sidespin is completely neglected.
        eff_top = [math.cos(a/180.0*math.pi) for a in self.motor_angles]
        if self.debug:
            print(f"{self.motor_angles=}")
            print(f"{eff_top=}")
        # default to requested ball speed
        speeds = [v_ball_norm for _ in self.motors]
        if self.debug:
            print(f"after speed init: {speeds=}")
        # calculate motor1 speed dependent on requested horiz. speed and motor0 speed 
        speeds[1] = (sum([abs(e) for e in eff_top]) * w_h_norm - eff_top[0] * speeds[0])/eff_top[1]
        if self.debug:
            print(f"after rotation calc: {speeds=}")
        # ensure requested ball speed (keeping the absolute rotation)
        avg = sum(speeds)/len(speeds) 
        delta = v_ball_norm - avg
        for i in range(len(speeds)):
            speeds[i] = speeds[i] + delta
        if self.debug:
            print(f"after ball speed calc: {speeds=}")
        # normalize to top speed (=1)
        # this linear scaling changes rotation and speed, but might be the best compromise
        max_spd = max(speeds)
        if max_spd > 1.0:
            for i in range(len(speeds)):
                speeds[i] = speeds[i]/max_spd
        if self.debug:
            print(f"after max speed calc: {speeds=}")
        # normalize to min speed (=-1)
        # this linear scaling changes rotation and speed, but might be the best compromise
        max_spd = -min(speeds)
        if max_spd > 1.0:
            for i in range(len(speeds)):
                speeds[i] = speeds[i]/max_spd
        if self.debug:
            print(f"after min speed calc: {speeds=}")
        
        # convert to percentage
        for i in range(len(speeds)):
            speeds[i] = speeds[i]*100
        if self.debug:
            print(f"after percentage conversion: {speeds=}")
        return [int(s) for s in speeds]

        # self.v_ball = v_ball_norm * self.v_ball_max # m/s
        # self.w_h = w_h_norm * self.w_h_max * 2 * math.pi # arc/s
        # self.w_v = w_v_norm * self.w_v_max * 2 * math.pi # arc/s

        # print(f"requested ball speed: {self.v_ball} m/s")
        # print(f"requested topspin: {self.w_h / 2 / math.pi} 1/s")
        # print(f"requested sidespin: {self.w_v / 2 / math.pi} 1/s")

        # # Calculate the surface speeds
        # v = [0.0, 0.0, 0.0]
        # v[2] = self.v_ball - 1/3*self.r_ball*self.w_h - math.sqrt(3)/6*self.r_ball*self.w_v
        # v[1] = math.sqrt(3)/2*self.r_ball*self.w_v + v[2]
        # v[0] = self.r_ball*self.w_h + (v[1]+v[2])/2

        # for i in range(len(self.motorSpeeds)):
        #     print(f"surface speed {i}: {v[i]} m/s")

        # # Calculate motor speeds
        # for i in range(len(self.motorSpeeds)):
        #     self.motorSpeeds[i] = v[i] / (self.d_wheel[i] * math.pi)
        #     print(f"motor speed {i}: {self.motorSpeeds[i]} 1/s")

        # for i in range(len(self.motors)):
        #     self.motors[i].SetSpeed(self.motorSpeeds[i])

    def setMotorSpeeds(self, motor_speeds: List[int]) -> None:
        """
        Sets the motors to the specified speeds.
        The speeds can be determined via method calc_motor_speeds().<br>
        Note that this will not start or stop actual operation, as this is dependent on the status.
        Parameters:
        motor_speeds: requested speed per motor, normalized to 100% (-100.0 to +100.0) 
        """
        if self.debug:
            print(f"set_motor_speeds({motor_speeds=})")
        if len(motor_speeds) != len(self.motorSpeeds):
            raise InputDataException("Invalid number of values in motor_speeds!")
        i = 0
        for spd in motor_speeds:
            if self.debug:
                print(f"motor speed {i}: {spd} %")
            self.motors[i].set_speed(spd)
            self.motorSpeeds[i] = spd
            i += 1

    def stop(self):
        """This will halt motor operation without changing the configured motor speeds."""
        self.status = 0 # halted

    @property
    def status(self) -> int:
        return self._status
    @status.setter
    def status(self, value: int):
        if value == 0:
            self._status = 0
            for motor in self.motors:
                motor.stop()
        else:
            self._status = 1
            self.setMotorSpeeds(self.motorSpeeds)


    def getStatusData(self) -> dict:
        ret = {}
        motors = []
        for motor in self.motors:
            motors.append(motor.getStatusData())
        ret['bd_number'] = self.bd_number
        ret['status'] = self._status
        ret['motors'] = motors
        return ret

    def getConfigData(self) -> dict:
        ret = {}
        motors = []
        for motor in self.motors:
            motors.append(motor.getConfigData())
        ret['bd_number'] = self.bd_number
        ret['motors'] = motors
        ret['motor_angles'] = self.motor_angles
        ret['wheel_diameters'] = self.wheel_diameters
        ret['motor_driver'] = self.motorDriver.getConfigData()
        return ret

if __name__ == "__main__":
    driver = BallDriver(0, debug=True)
    # speed up for a second
    driver.setMotorSpeeds(driver.calc_motor_speeds(.75, 0, 0))
    print(driver.getConfigData())
    time.sleep(1)
    driver.setMotorSpeeds(driver.calc_motor_speeds(0, 0, 0))

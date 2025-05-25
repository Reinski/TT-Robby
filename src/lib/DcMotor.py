# Copyright (c) 2023 Reiner Nikulski
# 
# This software is released under the MIT License.
# https://opensource.org/licenses/MIT
from Pca9685 import PCA9685

class DcMotor():
    MotorDirForward = (0,1)
    MotorDirBackward = (1,0)
    def __init__(self, driver: PCA9685, motor_number:int=0, polarity:int=1, debug:bool=False):
        """
        driver: The object for the motor driver
        motor_number: motor index on the driver board (0 to 3), determining the connection pins and channels.
        polarity: positive value means posititve speeds are in forward direction, negative value reverses this.
        debug: Enable debug output?
        """
        self.debug = debug
        if self.debug:
            print(f"Initializing {__class__.__name__} #{motor_number} with polarity {polarity}.")
        self.polarity = polarity
        if motor_number<0 or motor_number>3:
            raise Exception(f"Implementation error: Invalid motor number specified for DcMotor ({motor_number})!")
        self.pwm = driver
        self.motor_number = motor_number
        self.MotorPin = (motor_number*3,motor_number*3+1,motor_number*3+2) #['MA', 0,1,2, 'MB',3,4,5, 'MC',6,7,8, 'MD',9,10,11]
        if self.debug:
            print(f"MotorPin set to {self.MotorPin}.")
        """The channel(?) numbers on the driver board used for this motor, e.g. (0,1,2) for motor 0."""
        self.speed = 0
        self._last_speed = 0 
        """stores the last speed different from 0"""
        if self.debug:
            print(f"{__class__.__name__}: Init complete.")

    def set_speed(self, speed: int):
        """
        Sets the motor speed directly to the specified percentage of max power.
        Parameters:
        speed: motor speed from -100 (max reverse) to 0 (stop) to 100 (max forward speed)
        """
        if speed > 0:
            mDir = self.MotorDirForward if self._polarity > 0 else self.MotorDirBackward
            if speed > 100:
                speed = 100
        elif speed < 0:
            mDir = self.MotorDirBackward if self._polarity > 0 else self.MotorDirForward
            if speed < -100:
                speed = -100
            speed = -speed
        else:
            self.stop()
            return
        
        # help accelerating by setting to full speed
        # IMPROVE: This doesn't make sense: For ==0 ?! And should compare to previous speed!
        # IMPROVE: This whole logic belongs into the driver class, not the motor!
        if self.speed == 0:
            if (self.debug):
                print("set PWM PIN %d, speed %d" %(self.MotorPin[0], 100))
                print("set pin A %d , dir %d" %(self.MotorPin[1], mDir[0]))
                print("set pin B %d , dir %d" %(self.MotorPin[2], mDir[1]))

            self.pwm.setServoPulse(self.MotorPin[0], 100)        
            self.pwm.setLevel(self.MotorPin[1], mDir[0])
            self.pwm.setLevel(self.MotorPin[2], mDir[1])

        # set to the wanted speed
        if (self.debug):
            print("set PWM PIN %d, speed %d" %(self.MotorPin[0], speed))
            print("set pin A %d , dir %d" %(self.MotorPin[1], mDir[0]))
            print("set pin B %d , dir %d" %(self.MotorPin[2], mDir[1]))

        self.pwm.setServoPulse(self.MotorPin[0], speed)        
        self.pwm.setLevel(self.MotorPin[1], mDir[0])
        self.pwm.setLevel(self.MotorPin[2], mDir[1])

        if speed != 0:
            self._last_speed = speed
        self.speed = speed if speed > 0 else -speed

    def stop(self):
        if (self.debug):
            print("stopping motor on PIN %d" % self.MotorPin[0])
        self.pwm.setServoPulse(self.MotorPin[0], 0)
        self.pwm.setLevel(self.MotorPin[1], 0)
        self.pwm.setLevel(self.MotorPin[2], 0)
        self.speed = 0

    def start(self):
        if (self.debug):
            print("Starting motor on PIN %d with last used speed of %d." % (self.MotorPin[0], self._last_speed))
        self.set_speed(self._last_speed)
        
    def getStatusData(self) -> dict:
        return {
            'motor_number': self.motor_number,
            'speed': self.speed,
        }
    def getConfigData(self) -> dict:
        return {
            'motor_number': self.motor_number,
            'polarity': self._polarity,
            'debug': self.debug,
        }
    def setConfigData(self, data: dict) -> dict:
        tmp = data.get('polarity')
        if tmp:
            self.polarity = int(tmp)
        tmp = data.get('debug')
        if tmp:
            self.debug = bool(tmp)
        return self.getConfigData()
    
    @property
    def polarity(self) -> int:
        return self._polarity
    @polarity.setter
    def polarity(self, value: int):
        if value == 0:
            raise Exception(f"Config error: Invalid polarity (zero) specified for DcMotor {self.motor_number}!")
        self._polarity = 1 if value > 0 else -1

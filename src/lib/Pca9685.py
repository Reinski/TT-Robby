# Copyright (c) 2023 Reiner Nikulski
# 
# This software is released under the MIT License.
# https://opensource.org/licenses/MIT
import sys
if 'micropython' not in sys.version.lower():
    from typing import Union
from time import sleep
from machine import Pin, I2C
import math

# GPIO channel + pin(s) used on pico(!) for I2C addressing, PCA9685 supports channel 0 on GP20+GP21 or 1 on GP6+GP7
I2C_CHANNEL = 0
PIN_SDA = 20

class PCA9685:
    """The PCA9685 is a 16-channel, 12-bit PWM controller that is used to control DC motors.
    It communicates over I2C using only two pins on the controller board."""
    # Registers/etc.
    __SUBADR1            = 0x02
    __SUBADR2            = 0x03
    __SUBADR3            = 0x04
    __MODE1              = 0x00
    __PRESCALE           = 0xFE
    __LED0_ON_L          = 0x06
    __LED0_ON_H          = 0x07
    __LED0_OFF_L         = 0x08
    __LED0_OFF_H         = 0x09
    __ALLLED_ON_L        = 0xFA
    __ALLLED_ON_H        = 0xFB
    __ALLLED_OFF_L       = 0xFC
    __ALLLED_OFF_H       = 0xFD

    def __init__(self, address: Union[int, None]=0x40, debug=None, i2c_channel=I2C_CHANNEL, sda_pin=PIN_SDA):
        """Initializes the PCA9685 motor driver.
        Parameters:
        address: I2C address of the PCA9685 (default: 0x40)
        debug: Set to True to enable debug output (default: False)
        i2c_channel: I2C channel (default: 0)
        sda_pin: GP-pin number on the pico where the motor shield (pca9685) is connected (default: 20)"""
        self.debug = debug
        if self.debug:
            print(f"Init PCA9685: I2C pins sda={sda_pin} and scl={sda_pin+1} (channel {i2c_channel})")
        if not address:
            self.address = 0x40
        else:
            self.address = address
        self.sda_pin = sda_pin
        self.i2c_channel = i2c_channel
        self.i2c = I2C(i2c_channel, scl=Pin(sda_pin+1), sda=Pin(sda_pin), freq=100000)
        if self.debug:
            print(f"i2c scan shows these addresses: {[hex(a) for a in self.i2c.scan()]}") # I2C-Bus-Scan
            print(f"own address={hex(self.address)}")
        if (self.debug):
            print("Resetting PCA9685 now...")
        self.write(self.__MODE1, 0x00)
        if (self.debug):
            print("PCA9685 init complete.")
	
    def write(self, reg_address, value):
        """Writes an 8-bit value to the specified register/address on the I2C device."""
        self.i2c.writeto_mem(int(self.address), int(reg_address), bytes([int(value)]))
        if (self.debug):
            print("I2C: Write 0x%02X to register 0x%02X" % (value, reg_address))
	  
    def read(self, reg):
        """Read an unsigned byte from the I2C device"""
        rdate = self.i2c.readfrom_mem(int(self.address), int(reg), 1)
        if (self.debug):
            print("I2C: Device 0x%02X returned 0x%02X from reg 0x%02X" % (self.address, rdate[0], int(reg)))
        return rdate[0]
	
    def setPWMFreq(self, freq: float =50.0):
        """Sets the PWM frequency in Hz on the board.
        Parameters:
        freq: The frequency in Hz (default: 50)."""
        prescaleval = 25000000.0    # 25MHz of the internal clock
        prescaleval /= 4096.0       # 12-bit resolution
        prescaleval /= freq
        prescaleval -= 1.0
        if (self.debug):
            print("Setting PWM frequency to %d Hz" % freq)
            print("Estimated pre-scale: %d" % prescaleval)
        prescale = math.floor(prescaleval + 0.5)
        if (self.debug):
            print("Final pre-scale: %d" % prescale)

        oldmode = self.read(self.__MODE1)
        #print("oldmode = 0x%02X" %oldmode)
        newmode = (oldmode & 0x7F) | 0x10        # sleep
        self.write(self.__MODE1, newmode)        # go to sleep
        self.write(self.__PRESCALE, int(math.floor(prescale)))
        self.write(self.__MODE1, oldmode)
        sleep(0.005)
        self.write(self.__MODE1, oldmode | 0x80) # activate output pulse (questionalbe info from windsurf AI)

    def setPWM(self, channel: int, on: int, off: int):
        """Sets the PWM for a single channel.
        Parameters:
        channel: The PWM channel to set (0-15).
        on: sets the start of the PWM signal (0-4095).
        off: sets the end of the PWM signal (0-4095)."""
        self.write(self.__LED0_ON_L+4*channel, on & 0xFF)
        self.write(self.__LED0_ON_H+4*channel, on >> 8)
        self.write(self.__LED0_OFF_L+4*channel, off & 0xFF)
        self.write(self.__LED0_OFF_H+4*channel, off >> 8)
        if (self.debug):
            print("channel: %d  LED_ON: %d LED_OFF: %d" % (channel,on,off))
	  
    def setServoPulse(self, channel: int, pulse_pct: int):
        """Sets the pulse width for a servo motor on the specified channel.
        The pulse is given in percent of the maximum pulse width (100% = 4095).
        Parameters:
        channel: The PWM channel to set (0-15).
        pulse: The pulse width as a percentage (0-100).
        """
        pulse = int(pulse_pct * (4095.0 / 100.0))
        self.setPWM(channel, 0, pulse)
    
    def setLevel(self, channel: int, value: int):
        """Sets the level/pulse of a PWM channel to either high (1) or low (0).
        Parameters:
        channel: The PWM channel to set (0-15).
        value: 1 for high, 0 for low."""
        if (value > 0):
              self.setPWM(channel, 0, 4095)
        else:
              self.setPWM(channel, 0, 0)

    def getConfigData(self) -> dict:
        """Returns the configuration data for the PCA9685 as a dictionary."""
        return {
            'type': self.__class__.__name__,
            'address': self.address,
            'i2c_channel': self.i2c_channel,
            'sda_pin': self.sda_pin,
            'debug': self.debug,
        }
    def setConfigData(self, data: dict):
        """Sets the configuration data for the PCA9685 to a limited amount.
        Parameters:
        data: A dictionary containing the configuration data."""
        tmp = data.get('debug')
        if tmp is not None:
            self.debug = bool(tmp)
        return self.getConfigData()
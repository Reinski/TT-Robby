
from machine import Pin, PWM
import time

# DEFAULTS:
# The typical range for the sg92r servo is 0 to 180 degrees, which corresponds 
# to a duty cycle of 1ms (-90°) to 2ms (+90°) at a frequency of 50Hz (20ms pulse width).
FREQ = 50 # Hz
T_LOW = 0.5 # ms
T_HIGH = 2.5 # ms
HALFSPAN_ANGLE = 90 # degrees

class Sg92r:
    """Controls an SG92R servo motor."""
    def __init__(self, control_pin: int=1, freq=FREQ, t_low=T_LOW, t_high=T_HIGH, halfspan_angle=HALFSPAN_ANGLE, debug=False):
        self.debug = debug
        self._control_pin = control_pin
        self._t_low = t_low
        self._t_high = t_high
        self._freq = freq
        self._halfspan_angle = halfspan_angle
        self._derive_attributes()

    def _derive_attributes(self):
        """Sets the attributes that are derived from others."""
        self._t_pulse = 1000.0 / float(self._freq) # ms
        self._duty_halfspan = (self._t_high - self._t_low) / self._t_pulse * 65535 / 2
        self._duty_neutral = self._t_low / self._t_pulse * 65535 + self._duty_halfspan
        self._pwm = PWM(Pin(self._control_pin), freq=self._freq, duty_u16=int(self._duty_neutral))
    
    def set_servo_angle(self, angle):
        """Move the sg92r servo to an angle between -90 and +90 degrees."""
        # The typical range for the sg92r servo is 0 to 180 degrees, which corresponds to a 
        # duty cycle of 1ms (-90°) to 2ms (+90°) at a frequency of 50Hz (20ms pulse width).
        if angle > self._halfspan_angle:
            angle = self._halfspan_angle
        elif angle < -self._halfspan_angle:
            angle = -self._halfspan_angle
        duty_cycle = int(angle / self._halfspan_angle * self._duty_halfspan + self._duty_neutral)
        print("Current duty cycle:", self._pwm.duty_u16(), "/ angle: ", (self._pwm.duty_u16() - self._duty_neutral) / self._duty_halfspan * self._halfspan_angle)
        print("Moving to", angle, '/', duty_cycle)
        time.sleep(.1)
        self._pwm.duty_u16(duty_cycle)

    def getStatusData(self) -> dict:
        return {
            'current_duty': self._pwm.duty_u16(),
        }
    def getConfigData(self) -> dict:
        return {
            'type': type(self).__name__,
            'halfspan_angle': self._halfspan_angle,
            't_low': self._t_low,
            't_high': self._t_high,
            'freq': self._freq,
            'control_pin': self._control_pin,
        }
    def setConfigData(self, data: dict) -> dict:
        """Sets the object's attributes based on the configuration data."""
        tmp = data.get('motor_number')
        if tmp:
            self._motor_number = int(tmp)
        tmp = data.get('halfspan_angle')
        if tmp:
            self._halfspan_angle = int(tmp)
        tmp = data.get('t_low')
        if tmp:
            self._t_low = int(tmp)
        tmp = data.get('t_high')
        if tmp:
            self._t_high = int(tmp)
        tmp = data.get('freq')
        if tmp:
            self._freq = int(tmp)
        tmp = data.get('control_pin')
        if tmp:
            self._control_pin = int(tmp)
        self._derive_attributes()
        return self.getConfigData()

    def start(self):
        raise NotImplementedError("The start() method is not implemented for the Sg92r class.")

    def stop(self):
        raise NotImplementedError("The stop() method is not implemented for the Sg92r class.")
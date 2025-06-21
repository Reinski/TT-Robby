
from machine import Pin, PWM
import time

# DEFAULTS:
# The typical range for the sg92r servo is 0 to 180 degrees, which corresponds 
# to a duty cycle of approx. 1ms (-90°) to 2ms (+90°) at a frequency of 50Hz (20ms pulse width).
FREQ = 50 # Hz
T_LOW = 0.5 # ms - This is the hard limit to protect the motor from damage.
T_HIGH = 2.5 # ms - This is the hard limit to protect the motor from damage.
T_LOW_DEFAULT = 1.0 # ms
T_HIGH_DEFAULT = 2.0 # ms
HALFSPAN_ANGLE = 90 # degrees

class Sg92r:
    """Controls an SG92R servo motor.
    The SG92R is a PWM controlled servo, which can usually rotate 90° in both directions. It is connected to one PWM GPIO pin of the microcontroller.
    Parameters:
    """
    def __init__(self, control_pin: int=0, freq=FREQ, t_low=T_LOW_DEFAULT, t_high=T_HIGH_DEFAULT, halfspan_angle=HALFSPAN_ANGLE, sec_per_degree=0.1/60.0, debug=False):
        """Initializes the Sg92r servo motor with the given parameters.
        Args:
            control_pin (int): The GPIO pin number to be used for PWM (default: 0).
            freq (int): Frequency of the PWM signal in Hz (default: 50).
            t_low (float): Lower limit of the time of the PWM signal in milliseconds (default: 1.0).
            t_high (float): Upper limit of the time of the PWM signal in milliseconds (default: 2.0).
            halfspan_angle (int): Maximum angle in both directions of the servo in degrees (default: 90).
            sec_per_degree (float): Motion time of the servo in seconds per degree (default: 0.1sec/60.0°).
            debug (bool): If True, enables debug mode.
        """

        self.debug = debug
        self._sec_per_degree = sec_per_degree # degrees per second
        self._control_pin = control_pin
        self._t_low = max(t_low, T_LOW)
        self._t_high = min(t_high, T_HIGH)
        self._freq = freq
        self._halfspan_angle = halfspan_angle
        self.current_angle = 0.0 # current angle of the servo in degrees
        self._derive_attributes()

    def _derive_attributes(self):
        """Sets the attributes that are derived from others."""
        self._t_pulse = 1000.0 / float(self._freq) # ms
        self._duty_halfspan = (self._t_high - self._t_low) / self._t_pulse * 65535 / 2
        self._duty_neutral = self._t_low / self._t_pulse * 65535 + self._duty_halfspan
        self._pwm = PWM(Pin(self._control_pin), freq=self._freq, duty_u16=int(self._duty_neutral))
        if self.debug:
            print("Sg92r:")
            print(f"  {self._control_pin=}")
            print(f"  {self._t_low=}")
            print(f"  {self._t_high=}")
            print(f"  {self._freq=}")
            print(f"  {self._halfspan_angle=}")
            print(f"  {self._sec_per_degree=}")
            print(f"  {self._t_pulse=}")
            print(f"  {self._duty_halfspan=}")
            print(f"  {self._duty_neutral=}")
            print("Sg92r init complete.")
    
    def rotate_by_angle(self, angle: float, op_complete_callback=None):
        """Move the sg92r servo to an angle between its min and max angle.
        Args:
            angle (float): The angle to move the servo to, in degrees. 
                           Positive values are clockwise, negative values are counter-clockwise.  
            op_complete_callback (callable, optional): This function is there for compatibility with the method signature of the StepMotorPIO class. 
                                                       It is ignored, as the servo does not report back its position (is not encoded) or controls the movement, but rather moves immediately.
                                                       If an argument is specified here, then a waiting time is calculated based on the angle and the sec_per_degree attribute and the call is blocking for that amount of time.
        """
        # The typical range for the sg92r servo is 0 to 180 degrees, which corresponds to a 
        # duty cycle of 1ms (-90°) to 2ms (+90°) at a frequency of 50Hz (20ms pulse width).
        if angle > self._halfspan_angle:
            angle = self._halfspan_angle
        elif angle < -self._halfspan_angle:
            angle = -self._halfspan_angle
        duty_cycle = int(angle / self._halfspan_angle * self._duty_halfspan + self._duty_neutral)
        if self.debug:
            print("Current duty cycle:", self._pwm.duty_u16(), "/ angle: ", (self._pwm.duty_u16() - self._duty_neutral) / self._duty_halfspan * self._halfspan_angle)
            print("Moving to", angle, 'deg / duty', duty_cycle)
        #time.sleep(.1)
        self._pwm.duty_u16(duty_cycle)
        if op_complete_callback:
            wait_time = abs(angle-self.current_angle) * self._sec_per_degree
            time.sleep(wait_time)
        else:
            # TODO: Check if this is really required or if it is slowing down the operation unnecessarily.
            time.sleep(self._t_pulse / 1000)  # Wait one pulse cycle to ensure the servo has time to adopt the change.

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
            'sec_per_degree': self._sec_per_degree,
        }
    def setConfigData(self, data: dict) -> dict:
        """Sets the object's attributes based on the configuration data.
        Args:
            data (dict): A dictionary containing the configuration data.
        Returns:
            dict: The updated configuration data.
        """
        tmp = data.get('motor_number')
        if tmp:
            self._motor_number = int(tmp)
        tmp = data.get('halfspan_angle')
        if tmp:
            self._halfspan_angle = int(tmp)
        tmp = data.get('t_low')
        if tmp:
            self._t_low = max(float(tmp), T_LOW)
        tmp = data.get('t_high')
        if tmp:
            self._t_high = min(float(tmp), T_HIGH)
        tmp = data.get('freq')
        if tmp:
            self._freq = int(tmp)
        tmp = data.get('control_pin')
        if tmp:
            self._control_pin = int(tmp)
        tmp = data.get('sec_per_degree')
        if tmp:
            self._sec_per_degree = float(tmp)
        self._derive_attributes()
        return self.getConfigData()

    def start(self):
        raise NotImplementedError("The start() method is not implemented for the Sg92r class.")

    def stop(self):
        """This will bring the servo actively to the neutral position. A hard stop for a servo is not necessary, 
        as the servo is anyways stopped as long as no new angle is set."""

        if self.debug:
            print("Bringing Sg92r servo motor to neutral position.")
        self.rotate_by_angle(0.0)

from lib.StepMotorPIO import StepMotorPIO, MODE_COUNTED
from lib.sg92r import Sg92r


class MachineRotator:
    """
    Defines a joint, rotating the whole machine on a horizontal plane (vertical axis).
    Multiple motors can be used to rotate the machine, however, they must be coordinated/synced properly.
    """
    def __init__(self, min_angle_deg: float = -90.0, max_angle_deg: float = 90.0, debug: bool=False):
        self.debug = debug
        self.motors = []
        self.motor_angle_factors = []
        """motors which participate in the rotation."""
        self.min_angle_deg = min(min_angle_deg, max_angle_deg)
        self.max_angle_deg = max(min_angle_deg, max_angle_deg)
    
    def add_motor(self, motor, angle_factor: float=1.0):
        """
        Adds a motor to the list of motors that participate in the rotation.
        The according class must have a set_angle(angle_deg) method.
        The angle_factor parameter is used to scale the angle set for each motor.
        This is useful if not all motors are able to rotate the same amount or use gears etc.
        For example, if you have a motor that can rotate 90 degrees, but you
        want it to rotate the same amount as a motor that can rotate 180 degrees,
        you can set the angle_factor for the 90 degree motor to 0.5.
        parameters:
            motor: The motor object to add.
            angle_factor: The angle factor for this motor.
        """
        self.motors.append(motor)
        self.motor_angle_factors.append(angle_factor)

    def rotate(self, angle: float):
        """Rotates the machine to the given angle."""
        angle = max(min(angle, self.max_angle_deg), self.min_angle_deg)
        if self.debug:
            print("Rotating machine to %f degrees." % angle)
        for i, motor in enumerate(self.motors):
            motor.set_angle(angle * self.motor_angle_factors[i])

    def getConfigData(self):
        return {
            "min_angle_deg": self.min_angle_deg, 
            "max_angle_deg": self.max_angle_deg,
            "motors": [motor.getConfigData() for motor in self.motors],
            "motor_angle_factors": self.motor_angle_factors,
        }
    
    def setConfigData(self, data):
        self.min_angle_deg = data.get("min_angle_deg", -90.0)
        self.max_angle_deg = data.get("max_angle_deg", 90.0)
        self.motors = []
        for cfg_mot in data["motors"]:
            cfg = cfg_mot["config"]
            if cfg_mot['type'] == 'StepMotorPIO':
                motor = StepMotorPIO(mode=MODE_COUNTED, starting_gp_pin=cfg['starting_gp_pin'], consecutive_pins=cfg['consecutive_pins'], pio_block_index=cfg['pio_block_index'], debug=self.debug)
                motor.inner_motor_steps = cfg['inner_motor_steps']
                motor.gear_ratio = cfg['gear_ratio']
                motor.runner_freq = cfg['runner_freq']
                motor.correction_steps = cfg['correction_steps']
                motor.counter_freq = cfg['counter_freq']
            elif cfg_mot['type'] == 'Sg92r':
                motor = Sg92r(debug=self.debug)
                motor.setConfigData(cfg)
            self.motors.append(motor)
        self.motor_angle_factors = []
        for val in data["motor_angle_factors"]:
            self.motor_angle_factors.append(val)

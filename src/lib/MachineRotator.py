from lib.StepMotorPIO import StepMotorPIO, MODE_COUNTED
from lib.Sg92r import Sg92r
from lib.RobbyExceptions import ImplementationException, ConfigurationException


class MachineRotator:
    """
    Defines a joint, rotating the whole machine on a horizontal plane (vertical axis).
    Multiple motors can be used to rotate the machine, however, they must be coordinated/synced properly.
    """
    def __init__(self, mr_index: int, min_angle_deg: float = -45.0, max_angle_deg: float = 45.0, debug: bool=False):
        self.debug = debug
        self.mr_index = mr_index
        self.motors: list[StepMotorPIO | Sg92r] = []
        self.motor_angle_factors = []
        """motors which participate in the rotation."""
        self.min_angle_deg = min(float(min_angle_deg), float(max_angle_deg))
        self.max_angle_deg = max(float(min_angle_deg), float(max_angle_deg))
        if self.debug: 
            print(f"MachineRotator #{self.mr_index} initialized.")
    
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
            motor.rotate_by_angle(angle * self.motor_angle_factors[i])

    def getConfigData(self):
        return {
            "mr_index": self.mr_index,
            "debug": self.debug,
            "min_angle_deg": self.min_angle_deg, 
            "max_angle_deg": self.max_angle_deg,
            "motors": [motor.getConfigData() for motor in self.motors],
            "motor_settings": [{'angle_factor': self.motor_angle_factors[i]} for i in range(len(self.motor_angle_factors))],
        }
    
    def setConfigData(self, data):
        self.mr_index = int(data.get("mr_index", 0))
        self.debug = bool(data.get("debug", False))
        self.min_angle_deg = float(data.get("min_angle_deg", -45.0))
        self.max_angle_deg = float(data.get("max_angle_deg", 45.0))
        self.motors = []
        for cfg_mot in data["motors"]:
            if cfg_mot.get('type') == 'StepMotorPIO':
                motor = StepMotorPIO(mode=MODE_COUNTED, debug=self.debug)
            elif cfg_mot.get('type') == 'Sg92r':
                motor = Sg92r(debug=self.debug)
            else:
                if cfg_mot.get('type') is None:
                    raise ConfigurationException("Motor type is not specified in MachineRotator.setConfigData()")
                else:
                    raise ImplementationException(f"Motor type {cfg_mot['type']} is not implemented in MachineRotator.setConfigData()")
            motor.setConfigData(cfg_mot)
            self.motors.append(motor)
        self.motor_angle_factors = []
        for settings in data["motor_settings"]:
            self.motor_angle_factors.append(float(settings.get('angle_factor', 1.5)))
        if self.debug:
            print(f"MachineRotator #{self.mr_index} updated with data: {data}")
            print(f"Resulting config: {self.getConfigData()}")

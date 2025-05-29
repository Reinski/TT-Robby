from sg92r import Sg92r
from StepMotorPIO import StepMotorPIO, MODE_PERMANENT
from RobbyExceptions import ImplementationException

class BallStirrer:
    """This class provides the methods to control a ball stirrer.
    Ball stirrers are used to move or shake the balls inside the ball pool so that they are not jamming the outlet.
    Stirrers can be controlled by a stepper motor or a continuous servo and basically are only switched on and off.
    """
    def __init__(self, bs_index: int, motor, debug=False) -> None:
        self.bs_index = bs_index
        if motor:
            if type(motor) is not Sg92r and type(motor) is not StepMotorPIO:
                raise ImplementationException(f"BallStirrer #{self.bs_index}: Invalid motor type specified for BallStirrer ({type(motor)})!")
            else:
                self.motors = [motor]
        else:
            self.motors = []
        self.debug = debug
        self.running = False
        if self.debug: 
            print(f"BallStirrer #{self.bs_index} initialized with motor ", type(motor).__name__, ".") # debug

    def motor_start(self, motor_index: int):
        """Starts the specified motor. This method is a uniform testing method for the differnt motor types."""
        if self.debug:
            print(f"BallStirrer #{self.bs_index}: Starting motor {motor_index}.")
        motor = self.motors[motor_index]
        if type(motor) is StepMotorPIO:
            motor.rotate(1.0)
        else:
            motor.start() # type: ignore

    def start(self):
        """Starts the ball stirrer by starting all motors."""
        self.running = True
        for m in range (len(self.motors)):
            self.motor_start(m)

    def stop(self):
        """Stops the ball stirrer by stopping all motors."""
        self.running = False
        for m in self.motors:
            try:
                m.stop()
            except Exception as e:
                print(f"BallStirrer #{self.bs_index}: Error stopping motor: {e}")

    def getConfigData(self):
        config = {
            'bs_index': self.bs_index,
            'debug': self.debug,
            'motors': [],
            }
        for motor in self.motors:
            config['motors'].append(motor.getConfigData())
        return config
    
    def getStatusData(self):
        status = {
            'running': self.running,
            }
        return status

    def setConfigData(self, data: dict):
        if data.get('debug') is not None:
            self.debug = bool(data['debug'])
        if data.get('bs_index') is not None:
            self.bs_index = int(data['bs_index'])
        else:
            raise ImplementationException(f"BallStirrer load from config: No valid index specified in config data!")
        self.motors = []
        if 'motors' in data:
            for mot_cfg in data['motors']:
                if mot_cfg['type'] == 'Sg92r':
                    motor = Sg92r(debug=self.debug)
                elif mot_cfg['type'] == 'StepMotorPIO':
                    motor = StepMotorPIO(mode = MODE_PERMANENT, debug=self.debug)
                else:
                    raise ImplementationException(f"BallStirrer #{self.bs_index}: Invalid motor type specified in config data ({mot_cfg['type']})!")
                motor.setConfigData(mot_cfg)
                self.motors.append(motor)

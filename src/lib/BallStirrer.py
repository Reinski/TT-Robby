from sg92r import Sg92r
from StepMotorPIO import StepMotorPIO, MODE_PERMANENT

class BallStirrer:
    """This class provides the methods to control a ball stirrer.
    Ball stirrers are used to move or shake the balls inside the ball pool so that they are not jamming the outlet.
    Stirrers can be controlled by a stepper motor or a continuous servo and basically are only switched on and off.
    """
    def __init__(self, motor, debug=False) -> None:
        self.debug = debug
        self.motor = motor
        self.running = False
        if self.debug: 
            print("BallStirrer initializing with motor ", type(self.motor).__name__, ".") # debug
        if type(self.motor) is not Sg92r and type(self.motor) is not StepMotorPIO:
            raise Exception(f"Implementation error: Invalid motor type specified for BallStirrer ({type(self.motor)})!")

    def start(self):
        self.running = True
        if type(self.motor) is StepMotorPIO:
            self.motor.rotate(1.0)
        else:
            self.motor.start() # type: ignore

    def stop(self):
        self.running = False
        self.motor.stop()

    def getConfigData(self):
        config = {
            'config': self.motor.getConfigData()
            }
        return config
    
    def getStatusData(self):
        status = {
            'running': self.running,
            }
        return status

    def setConfigData(self, data: dict):
        if data['type'] == 'Sg92r':
            self.motor = Sg92r(debug=self.debug)
        elif data['type'] == 'StepMotorPIO':
            self.motor = StepMotorPIO(mode = MODE_PERMANENT, debug=self.debug)
        self.motor.setConfigData(data['config'])

from StepMotorPIO import StepMotorPIO, MODE_COUNTED

class BallFeeder:
    def __init__(self, motor, debug=False) -> None:
        self.debug = debug
        self.running = False
        self.motor = motor

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
            'motor': self.motor.getConfigData()
            }
        return config
    
    def getStatusData(self):
        status = {
            'running': self.running,
            }
        return status
    
    def setConfigData(self, data: dict):
        if data['type'] == 'Sg92r':
            raise NotImplementedError("The SetConfigData() method is not implemented for the Sg92r class.")
            #self.motor = Sg92r(debug=self.debug)
        elif data['type'] == 'StepMotorPIO':
            self.motor = StepMotorPIO(mode = MODE_COUNTED, debug=self.debug)
        self.motor.setConfigData(data['config'])

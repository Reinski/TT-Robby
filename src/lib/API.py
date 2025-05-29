from lib import RobbyController


class API:
    """This class encapsulates all API functions, so they can be used in different implementations, like REST, MQTT or even physical controls."""
    def __init__(self, controller: RobbyController.RobbyController, debug=False):
        """This class is meant to be instantiated by the RobbyController itself."""
        self.debug = debug
        self.controller = controller

    def set_mode(self, mode: int):
        self.controller.mode = mode
        
    def start_playing(self):
        self.controller._start_playing()

    def stop_playing(self):
        self.controller._stop_playing()

    def save_settings(self):
        self.controller._save_settings()

    def load_settings(self):
        self.controller._load_settings()

    def bd_start_motors(self, bd_number: int, speed: int = 100):
        """
        Start the motors of a ball driver with the given speed.

        Parameters:
        bd_number: number of the ball driver (int)
        speed: speed as integer between -100 and +100 (default: 100)
        """
        for motor in self.controller.ballDrivers[bd_number].motors:
            motor.set_speed(speed)

    def bd_stop_motors(self, bd_number: int):
        self.controller.ballDrivers[bd_number].stop()

    def bd_set_motor_speed(self, bd_number: int, motor_index: int, spd: float):
        """
        Set the speed of a single motor in a ball driver.

        Parameters:
        bd_number: number of the ball driver (int)
        motor_index: motor index (int)
        spd: speed as integer between -100 and +100
        """

        self.controller.ballDrivers[bd_number].motors[motor_index].set_speed(int(spd))

    # TODO: Ball stirrers and feeders are currently hardcoded as stepMotors. Motor type must be flexible!
    def bs_get_motor_config(self, bs_index: int):
        return self.controller.ball_stirrers[bs_index].getConfigData()

    def bs_start(self, bs_index: int):
        """
        Start a ball stirrer. 
        Parameters:
        bs_index: index of the ball stirrer (int)
        """
        self.controller.ball_stirrers[bs_index].start()

    def bs_stop(self, bs_index: int):
        """
        Stop a ball stirrer.
        Parameters:
        bs_index: index of the ball stirrer (int)
        """
        self.controller.ball_stirrers[bs_index].stop()

    def bs_motor_start(self, bs_index: int, motor_index: int):
        """
        Start a motor in a ball stirrer. This should be used e.g. during calibration.
        Parameters:
        bs_index: index of the ball stirrer (int)
        motor_index: index of the motor within the stirrer (int)
        """
        self.controller.ball_stirrers[bs_index].motor_start(motor_index)
    
    def bs_motor_stop(self, bs_index: int, motor_index: int):
        """
        Stop a motor in a ball stirrer.
        Parameters:
        bs_index: index of the ball stirrer (int)
        motor_index: index of the motor within the stirrer (int)
        """
        self.controller.ball_stirrers[bs_index].motors[motor_index].stop()

    def bf_get_motor_config(self, bf_index: int):
        return self.controller.ball_feeders[bf_index].getConfigData()
    
    def bf_motor_rotate(self, bf_index: int, motor_index: int, angle_deg: float):
        """
        Rotate a motor in a ball feeder by a given angle. This should be used e.g. during calibration.
        Parameters:
        bf_index: index of the ball feeder (int)
        motor_index: index of the motor within the feeder (int)
        angle_deg: angle in degrees (negative value moves into opposite direction)
        """
        self.controller.ball_feeders[bf_index].motors[motor_index].rotate_by_angle(angle_deg)
    
    def bf_motor_stop(self, bf_index: int, motor_index: int):
        """
        Stop a motor in a ball feeder.
        Parameters:
        bf_index: index of the ball feeder (int)
        motor_index: index of the motor within the feeder (int)
        """
        self.controller.ball_feeders[bf_index].motors[motor_index].stop()

    def bd_get_motor_config(self, bd_index: int, motor_index: int):
        return self.controller.ballDrivers[bd_index].motors[motor_index].getConfigData()
    def bd_set_motor_config(self, bd_index: int, motor_index: int, data: dict):
        self.controller.ballDrivers[bd_index].motors[motor_index].setConfigData(data)

    def get_machine_rotator_config(self, mr_index: int):
        if mr_index >= 0:
            return self.controller.machine_rotators[mr_index].getConfigData()
        else:
            return [mr.getConfigData() for mr in self.controller.machine_rotators]

    def set_machine_rotator_config(self, mr_index: int, data: dict):
        self.controller.machine_rotators[mr_index].setConfigData(data)

    def set_ball_acceleration(self, bd_index: int, velocity: float, topspin: float, sidespin: float):
        """
        Set the acceleration of a ball driver.

        Parameters:
        bd_number: number of the ball driver (int)
        velocity: velocity as float between 0.0 and 1.0
        topspin: float between -1.0 (backspin) and +1.0 (topspin)
        sidespin: sidespin as float between -1.0 (left) and +1.0 (right)
        """
        return self.controller.set_ball_acceleration(bd_index, velocity, topspin, sidespin)
    

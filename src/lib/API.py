from lib import RobbyController


class API:
    """This class encapsulates all API functions, so they can be used in different implementations, like REST, MQTT or even physical controls."""
    def __init__(self, controller: RobbyController.RobbyController, debug=False):
        """This class is meant to be instantiated by the RobbyController itself."""
        self.debug = debug
        self.controller = controller

    def set_mode(self, mode: int = -1, mode_text: str = ''):
        """Set the current mode of the controller.
        If mode is <0, the mode will be set by mode_text.
        Parameters:
        mode: mode as integer
        mode_text: text representation of the mode (only considered if mode < 0 or is omitted)
        """
        if mode >= 0:
            self.controller.mode = mode
        elif mode_text == '':
            raise ValueError("Mode text must be provided if mode is < 0.")
        else:
            modes = [k for k, v in RobbyController.MODE_TEXTS.items() if v == mode_text]
            if len(modes) < 1:
                raise ValueError(f"Invalid mode text specified: {mode_text}")
        self.controller.mode = modes[0]

    def get_mode(self) -> dict:
        return {'mode': self.controller.mode, 'mode_text': self.controller.mode_text}


    def start_playing(self):
        self.controller._start_playing()

    def stop_playing(self):
        self.controller._stop_playing()

    def save_settings(self):
        """Make the current settings of the controller permanent by saving them to the default file.
        This will overwrite the existing settings file.
        """
        self.controller._save_settings()

    def save_settings_as(self, filename: str):
        """Make the current settings of the machine permanently available, but not as the default.
        This will save the settings to the given file, overwriting an existing file with that name.
        """
        self.controller._save_settings(filename)

    def load_settings(self):
        self.controller._load_settings()

    def load_settings_from_file(self, filename: str):
        """Load settings from the given file.
        This will change the current settings of the machine, but without overwriting the default settings used at next startup.
        """
        self.controller._load_settings(filename)

    def bd_start(self, bd_number: int):
        """
        Start the ball driver with the given number.
        This will start all motors of the ball driver with their last used speed.
        Parameters:
        bd_number: number of the ball driver (int)
        """
        self.controller.ball_drivers[bd_number].start()
    def bd_stop(self, bd_number: int):
        """
        Stop the ball driver with the given number.
        This will stop all motors of the ball driver.
        Parameters:
        bd_number: number of the ball driver (int)
        """
        self.controller.ball_drivers[bd_number].stop()

    def bd_start_motors(self, bd_number: int, speed: int = 100):
        """
        Start the motors of a ball driver with the given speed.

        Parameters:
        bd_number: number of the ball driver (int)
        speed: speed as integer between -100 and +100 (default: 100)
        """
        for motor in self.controller.ball_drivers[bd_number].motors:
            motor.set_speed(speed)

    def bd_stop_motors(self, bd_number: int):
        self.controller.ball_drivers[bd_number].stop()

    def bd_set_motor_speed(self, bd_number: int, motor_index: int, spd: float):
        """
        Set the current speed of a single motor in a ball driver.

        Parameters:
        bd_number: number of the ball driver (int)
        motor_index: motor index (int)
        spd: speed as integer between -100 and +100
        """
        self.controller.ball_drivers[bd_number].motors[motor_index].set_speed(int(spd))

    def set_continuous_shot(self, data: dict):
        """
        Set the current shot.
        Parameters:
        data: shot data as dictionary, can contain 'velocity', 'topspin', 'sidespin'
        """
        v = data.get('velocity')
        if v:
            v = float(v)
        w_h = data.get('topspin')
        if w_h:
            w_h = float(w_h)
        w_v = data.get('sidespin')
        if w_v:
            w_v = float(w_v)
        self.controller.set_continuous_shot(v_ball_norm=v, w_h_norm=w_h, w_v_norm=w_v)

    def bd_set_current_shot(self, bd_index: int, shot: dict):
        """
        Set the current shot for a ball driver.
        Parameters:
        bd_index: index of the ball driver (int)
        shot: shot data as dictionary
        """
        v = shot.get('velocity')
        if v:
            v = float(v)
        w_h = shot.get('topspin')
        if w_h:
            w_h = float(w_h)
        w_v = shot.get('sidespin')
        if w_v:
            w_v = float(w_v)
        self.controller.ball_drivers[bd_index].update_current_shot(v_ball_norm=v, w_h_norm=w_h, w_v_norm=w_v)

    def bd_get_status(self, bd_index: int):
        """
        Get the status data of a ball driver.
        Parameters:
        bd_index: index of the ball driver (int)
        Returns:
        dict: Status data of the ball driver.
        """
        return self.controller.ball_drivers[bd_index].getStatusData()
    
    # TODO: Ball stirrers and feeders are currently hardcoded as stepMotors. Motor type must be flexible!
    def bs_get_config(self, bs_index: int):
        """Get the configuration data of a ball stirrer.
        Parameters:
        bs_index: index of the ball stirrer (int)
        Returns:
        dict: Configuration data of the ball feeder.
        """
        return self.controller.ball_stirrers[bs_index].getConfigData()
    def bs_set_config(self, bs_index: int, data: dict):
        """Set the configuration data of a ball stirrer.
        Parameters:
        bs_index: index of the ball stirrer (int)
        data: configuration data as dictionary
        Returns:
        dict: The updated configuration data.
        """
        return self.controller.ball_stirrers[bs_index].setConfigData(data)

    def bs_get_motor_config(self, bs_index: int, motor_index: int):
        """Get the configuration data of a motor in a ball stirrer.
        Parameters:
        bs_index: index of the ball stirrer (int)
        motor_index: index of the motor within the stirrer (int)
        Returns:
        dict: Configuration data of the motor.
        """
        return self.controller.ball_stirrers[bs_index].motors[motor_index].getConfigData()

    def bs_set_motor_config(self, bs_index: int, motor_index: int, data: dict):
        """Set the configuration data of a motor in a ball stirrer.
        Parameters:
        bs_index: index of the ball stirrer (int)
        motor_index: index of the motor within the stirrer (int)
        data: configuration data as dictionary
        Returns:
        dict: The updated configuration data.
        """
        return self.controller.ball_stirrers[bs_index].motors[motor_index].setConfigData(data)

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

    def bf_get_config(self, bf_index: int):
        """Get the configuration data of a ball feeder.
        Parameters:
        bf_index: index of the ball feeder (int)
        Returns:
        dict: Configuration data of the ball feeder.
        """
        return self.controller.ball_feeders[bf_index].getConfigData()
    def bf_set_config(self, bf_index: int, data: dict):
        """Set the configuration data of a ball feeder.
        Parameters:
        bf_index: index of the ball feeder (int)
        data: configuration data as dictionary
        Returns:
        dict: The updated configuration data.
        """
        return self.controller.ball_feeders[bf_index].setConfigData(data)
    
    def bf_get_motor_config(self, bf_index: int, motor_index: int):
        """Get the configuration data of a specific ball feeder motor.
        Parameters:
        bf_index: index of the ball feeder (int)
        motor_index: index of the motor within the feeder (int)
        Returns:
        dict: Configuration data of the ball feeder motor.
        """
        return self.controller.ball_feeders[bf_index].motors[motor_index].getConfigData()
    def bf_set_motor_config(self, bf_index: int, motor_index: int, data: dict):
        """Set the configuration data of a specific ball feeder motor.
        Parameters:
        bf_index: index of the ball feeder (int)
        motor_index: index of the motor within the feeder (int)
        data: configuration data as dictionary
        Returns:
        dict: The updated configuration data.
        """
        return self.controller.ball_feeders[bf_index].motors[motor_index].setConfigData(data)

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
        """Get the configuration data of a specific ball driver motor.
        Parameters:
        bd_index: index of the ball driver (int)
        motor_index: index of the motor within the driver (int)
        Returns:
        dict: Configuration data of the ball driver motor.
        """
        return self.controller.ball_drivers[bd_index].motors[motor_index].getConfigData()
    def bd_set_motor_config(self, bd_index: int, motor_index: int, data: dict):
        """Set the configuration data of a specific ball driver motor.
        Parameters:
        bd_index: index of the ball driver (int)
        motor_index: index of the motor within the driver (int)
        data: configuration data as dictionary
        Returns:
        dict: The updated configuration data.
        """
        return self.controller.ball_drivers[bd_index].motors[motor_index].setConfigData(data)

    def mr_rotate(self, mr_index: int, angle_deg: float):
        """
        Rotates the machine rotator by a given angle.
        Parameters:
        mr_index: index of the machine rotator (int)
        angle_deg: angle in degrees (negative value moves into opposite direction)
        """
        self.controller.machine_rotators[mr_index].rotate(angle_deg)

    def mr_motor_rotate_max(self, mr_index: int, motor_index: int):
        """
        Rotate a motor in a machine rotator to its maximum position. This should be used e.g. during calibration.
        Parameters:
        mr_index: index of the machine rotator (int)
        motor_index: index of the motor within the rotator (int)
        """
        self.controller.machine_rotators[mr_index].motors[motor_index].rotate_by_angle(float(self.controller.machine_rotators[mr_index].motors[motor_index]._halfspan_angle if self.controller.machine_rotators[mr_index].motors[motor_index].__class__.__name__=='Sg92r' else 45.0)) # type: ignore
    def mr_motor_rotate_min(self, mr_index: int, motor_index: int):
        """
        Rotate a motor in a machine rotator to its minimum position. This should be used e.g. during calibration.
        Parameters:
        mr_index: index of the machine rotator (int)
        motor_index: index of the motor within the rotator (int)        
        """
        self.controller.machine_rotators[mr_index].motors[motor_index].rotate_by_angle(float(-self.controller.machine_rotators[mr_index].motors[motor_index]._halfspan_angle if self.controller.machine_rotators[mr_index].motors[motor_index].__class__.__name__=='Sg92r' else -45.0)) # type: ignore

    def mr_motor_rotate(self, mr_index: int, motor_index: int, angle_deg: float):
        """
        Rotate a motor in a machine rotator by a given angle. This should be used e.g. during calibration.
        Parameters:
        mr_index: index of the machine rotator (int)
        motor_index: index of the motor within the rotator (int)
        angle_deg: angle in degrees (negative value moves into opposite direction)
        """
        self.controller.machine_rotators[mr_index].motors[motor_index].rotate_by_angle(angle_deg)
    
    def mr_get_config(self, mr_index: int):
        """Get the configuration data of a machine rotator.
        Parameters:
        mr_index: index of the machine rotator (int)
        Returns:
        dict: Configuration data of the machine rotator.
        list: If mr_index is -1, returns a list of all machine rotators' configuration data.
        """
        if mr_index >= 0:
            return self.controller.machine_rotators[mr_index].getConfigData()
        else:
            return [mr.getConfigData() for mr in self.controller.machine_rotators]

    def mr_set_config(self, mr_index: int, data: dict):
        """Set the configuration data of a machine rotator.
        Parameters:
        mr_index: index of the machine rotator (int)
        data: configuration data as dictionary
        Returns:
        dict: The updated configuration data.
        """
        return self.controller.machine_rotators[mr_index].setConfigData(data)

    def mr_get_motor_config(self, mr_index: int, motor_index: int):
        """Get the configuration data of a specific machine rotator motor.
        Parameters:
        mr_index: index of the machine rotator (int)
        motor_index: index of the motor within the rotator (int)
        Returns:
        dict: Configuration data of the machine rotator motor.
        """
        return self.controller.machine_rotators[mr_index].motors[motor_index].getConfigData()
    
    def mr_set_motor_config(self, mr_index: int, motor_index: int, data: dict):
        """Set the configuration data of a specific machine rotator motor.
        Parameters:
        mr_index: index of the machine rotator (int)
        motor_index: index of the motor within the rotator (int)
        data: configuration data as dictionary
        Returns:
        dict: The updated configuration data.
        """
        return self.controller.machine_rotators[mr_index].motors[motor_index].setConfigData(data)

    

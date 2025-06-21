from StepMotorPIO import StepMotorPIO, MODE_COUNTED
from RobbyExceptions import InvalidOperationException

class BallFeeder:
    """BallFeeder is responsible for dispensing singel balls controlling one or more motors."""
    def __init__(self, motor, bf_index: int, action_cycle: list = [-77], mounting_index: int = 0, debug=False) -> None:
        """Initialize the BallFeeder with a motor and a push cycle.  
        Args:
            motor (StepMotorPIO): The motor to be used for dispensing balls.
            bf_index (int): The index of the ball feeder, used for identification.
            action_cycle (list): A list of steps to perform for each ball dispensed. 
                               These steps can represent angles, number of steps to rotate a stepmotor or even pause times.
                               The actual interpretation depends on the motor type.
            mounting_index (int): The index in the action cycle where the motor is meant to be when mounted.
            debug (bool): If True, enables debug mode.
        """
        if mounting_index < 0 or mounting_index >= len(action_cycle):
            raise ValueError(f"Mounting index {mounting_index} is out of bounds for action cycle of length {len(action_cycle)}.")
        self.debug = debug
        self.bf_index = bf_index
        self.motors = [motor]
        self.motor_states = [[-1, action_cycle, mounting_index]]
        """list containing additional data per motor:
           - action cycle: e.g. a list of angles to rotate
           - current index: the current index in the action cycle, -1 if no action is running
           - mounting position: the index in the action cycle, where the motor is meant to be when mounted.
             This is used to move the motor accordingly into parking position after it has been mounted.
        """

    def dispense(self, controller_callback=None):
        """Dispense a ball by performing the predefined action with the motor."""
        if self.is_busy():
            raise InvalidOperationException("Ball Feeder should dispense, but is not finished with previous operation.")
        if self.debug:
            print(f"Ball Feeder releasing next ball.")
        
        self.current_ballfeeder_cycle_index = 0
        self.controller_callback = controller_callback
        for m in range(len(self.motors)):
            mot = self.motors[m]
            mot_states = self.motor_states[m]
            mot_states[0] = current_action_index = 0
            action_cycle = mot_states[1]
            mot.rotate_by_angle(angle=action_cycle[current_action_index], op_complete_callback=self._ball_feeder_next_step)

    def prepare_after_mount(self) -> None:
        """Move the ball feeder from the mounting position (mount_index) into waiting position.
           This is done by setting the current position to the mount_index and then performing the remaining steps in the action cycle.
        """
        # Waiting position is after the last step of the ball feeder cycle. 
        if self.is_busy():
            raise InvalidOperationException("Ball Feeder is currently operating and cannot be moved into the waiting position!")
        if self.debug:
            print(f"Ball Feeder preparing after mount")
        for m in range(len(self.motors)):
            motor = self.motors[m]
            state = self.motor_states[m]
            state[0] = state[2]  # set the current action index to the mounting index
            self._ball_feeder_next_step(motor)  # this will trigger the next step in the action cycle

    def _ball_feeder_next_step(self, mot):
        """Callback function to be called when the motor has completed a step in the action cycle.
           Checks whether a followup action is needed and triggers it or if not, finalizes the operation."""
        if self.debug:
            print(f"Ball Feeder #{self.bf_index}: motor step complete.")
        m = self.motors.index(mot)
        cycle_index = self.motor_states[m][0]
        cycle = self.motor_states[m][1]
        if self.debug:
            print(f"Motor #{m} identified. Current cycle index: {cycle_index}, cycle length: {len(cycle)}")
        cycle_index += 1
        if cycle_index >= len(cycle):
            # reached end of cycle --> waiting position
            if self.debug:
                print(f"Action cycle complete. {self.is_busy=}")
            self.motor_states[m][0] = -1
            # Moved to the async handling in run()
            # # set the machine status according to the current operation
            # self._status = self._status_requested
            # if self.debug:
            #     print(f"Machine status = {self._status}")
            #call back the controller if everything is done
            if not self.is_busy and self.controller_callback is not None:
                if self.debug:
                    print(f"BallFeeder #{self.bf_index} finished dispensing. Calling controller callback.")
                self.controller_callback()
            return
        self.motor_states[m][0] = cycle_index # update with the new index
        mot.rotate_by_angle(angle=cycle[cycle_index], op_complete_callback=self._ball_feeder_next_step)

    def is_busy(self) -> bool:
        for state in self.motor_states:
            if state[0] >= 0:
                return True
        return False
    

    # def start(self):
    #     self.running = True
    #     if type(self.motor) is StepMotorPIO:
    #         self.motor.rotate(1.0)
    #     else:
    #         self.motor.start() # type: ignore

    def stop(self):
        """Will bring the motors to an immediate halt. Will not reset motor states."""
        i = 0
        for m in self.motors:
            try:
                m.stop()
                i += 1
            except Exception as e:
                print(f"BallFeeder #{self.bf_index}: Error stopping motor #{i}: {e}")

    def getConfigData(self):
        config = {
            'bf_index': self.bf_index,
            'motors': [mot.getConfigData() for mot in self.motors],
            'motor_states': [ 
                {'action_cycle': s[1], 'mounting_index': s[2]} for s in self.motor_states
                ],
            }
        return config
    
    def getStatusData(self):
        status = {
            'is_busy': self.is_busy(),
            'motor_states': [ {'current_action_index': s[0], 'total_actions': len(s[1])} for s in self.motor_states],
            }
        return status
    
    def setConfigData(self, data: dict):
        """Adopts all settings from a serialized config. Existing settings will be overwritten."""

        self.motors = []
        self.bf_index = data.get('bf_index', 0)
        for mot_cfg in data.get('motors', []):
            # if mot['type'] == 'Sg92r':
            #     raise NotImplementedError("The SetConfigData() method is not implemented for the Sg92r class.")
            #     #self.motor = Sg92r(debug=self.debug)
            if mot_cfg['type'] == 'StepMotorPIO':
                motor = StepMotorPIO(mode = MODE_COUNTED, debug=self.debug)
            else:
                raise NotImplementedError(f"Motor type {mot_cfg['type']} is not implemented in BallFeeder.setConfigData()")
            motor.setConfigData(mot_cfg)
            self.motors.append(motor)

        self.motor_states = []
        for state_cfg in data.get('motor_states', []):
            self.motor_states.append([
                -1,  # current action index
                state_cfg.get('action_cycle', []),  # action cycle
                state_cfg.get('mounting_index', -1)  # mounting index
            ])

        if self.debug:
            print(f"BallFeeder initialized with data: {data}")
            print(f"Resulting config: {self.getConfigData()}")

def create_from_config(bf_cfg: dict, bf_index: int, debug=False) -> BallFeeder:
    """Factory function to create a BallFeeder instance from a serialized configuration.  
    Args:
        bf_cfg (dict): The serialized config.
        bf_index (int): The index of the ball feeder, used for identification.
        mounting_index (int): The index in the action cycle where the motor is meant to be when mounted.
        debug (bool): If True, enables debug mode.
    
    Returns:
        BallFeeder: An instance of the BallFeeder class.
    """
    # instantiate with default values, which will be overwritten afterwards by the config data
    bf = BallFeeder(motor=None, bf_index=bf_index, debug=debug)
    bf.setConfigData(bf_cfg)
    return bf
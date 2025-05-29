# Copyright (c) 2023 Reiner Nikulski
# 
# This software is released under the MIT License.
# https://opensource.org/licenses/MIT
from machine import Pin
import time
from math import ceil
from RobbyExceptions import ConfigurationException

MODE_UNSET = 0
MODE_COUNTED = 1
MODE_PERMANENT = 2
MODE_INTERVAL = 3
SM_MIN_FREQ = 1908
TICKS_PER_CYCLE = 192 # duration of the PIO loop for one cylce of the inner motor (one iteration of the runner code)

# Installation instructions with ULN2003 Stepper Motor Driver Module
# - Connect motor to driver module (simply plug in)
# - Wire the input signals (IN1 to IN4 on the module), beginning from the starting_gp_pin (specified for class constructor) on the pico.
# - Wire the power supply to driver module, either from pico or from external source.
class StepMotorPIO:
    """Class provides the internal functions to control a single stepper motor via PIO and 2 state machines.
       This can be used for alternating back/forth movement (ball pusher) or for constant (or repeating) movement into one direction.  
       The class provides these high-level methods:
       - rotate(): perform an async rotation into one direction until stop() is called
       - rotate_by_angle(): perform an async rotation by the given angle. A callback informs the caller when it is finished.
       - stop(): stop all current operation
    """
    def __init__(self, mode: int, gear_ratio = 64, inner_motor_steps = 32, correction_steps = -4, starting_gp_pin = 2, consecutive_pins = 4, pio_block_index = 0, runner_freq = 20000, counter_freq = 2000, debug=None):
        """Parameters:
           mode:              Mode of operation: MODE_COUNTED or MODE_PERMANENT
           gear_ratio:        See specs of the step motor.
           inner_motor_steps: See specs of the step motor.
           correction_steps:  This value is added to the number of inner steps required for a full rotation and is used to reflect deviations from the motor's theoretical gear ratio.
           starting_gp_pin:   GPIO-Index of the first of the consecutive pins the motor is connected to.
           consecutive_pins:  Total number of consecutive pins the motor is connected to.
           pio_block_index:   Pico has two pio blocks, so this can be 0 or 1 only (note that not all statemachines might be available dur to internal usage, e.g. for wlan!).
           runner_freq:       The frequency (Hz) to operate the state machines for driving the motor forward/backward.
           counter_freq:      The frequency (Hz) to operate the state machine for controlling the number of motor steps.
        """
        self.debug = debug
        self.mode = mode
        self._operating = False
        self._current_direction = 0
        self._counter_sm = None
        self._runner_fwd_sm = None
        self._runner_bwd_sm = None
        self._op_complete_callback = None
        # basic config
        self.starting_gp_pin = starting_gp_pin
        self.consecutive_pins = consecutive_pins
        self.gear_ratio = gear_ratio # speed variation ratio
        self.inner_motor_steps = inner_motor_steps
        self.correction_steps = correction_steps
        self.runner_freq = runner_freq
        self.counter_freq = counter_freq
        self.pio_block_index = min(max(pio_block_index, 0),1)
        self.adopt_config()

    def adopt_config(self):        
        # derived config
        self.pins = [Pin(i, Pin.OUT) for i in range(self.starting_gp_pin, self.starting_gp_pin + self.consecutive_pins)]
        self.full_rotation_steps = ((self.gear_ratio * self.inner_motor_steps) + self.correction_steps) / len(self.pins)  # 64*32 = 2048 steps -> 2048-4 / 4 = 511 (a step is a full cycle for the coils)
        self.angle_per_step = 360.0 / self.full_rotation_steps   # 0.7045° per step
        if self.debug:
            print("StepMotorPIO:")
            print(f"  {self.gear_ratio=}")
            print(f"  {self.inner_motor_steps=}")
            print(f"  {self.full_rotation_steps=}")
            print(f"  {self.angle_per_step=}")
            print(f"  {self.pins=}")
            print(f"  {self.pio_block_index=}")
            print("StepMotorPIO init complete.")

    def v2_create_statemachines(self, runner_freq = 20000, counter_freq = 2000):
        """Create the statemachines for the specified mode."""
        if self.debug:
            print("create_my_statemachines()")
        try:
            #rp2.PIO(self.pio_block_index).remove_program() # clear all programs from PIO block
            if self.mode == MODE_COUNTED:
                if self.debug:
                    print("removing pio programs for counted mode")
                rp2.PIO(self.pio_block_index).remove_program(trigger_steps)
                rp2.PIO(self.pio_block_index).remove_program(run_forward_pio)
                rp2.PIO(self.pio_block_index).remove_program(run_backward_pio)
            elif self.mode == MODE_PERMANENT:
                if self.debug:
                    print("removing pio programs for permanent mode")
                rp2.PIO(self.pio_block_index).remove_program(run_endless_pio)
        except Exception as e:
            if self.debug:
                print(f"Could not remove PIO programs: {str(e)}")
        # This whole dynamic handling is no longer required, as there are basically just two modes of operation to distinguish:
        # - run endlessly in either direction or
        # - run for specific time in either direction (meaning there steps are counted and callback is possible)
        self._counter_sm = None
        self._runner_fwd_sm = None
        self._runner_bwd_sm = None
        base_sm_index = self.pio_block_index * 4 # PIO0: 0-3; PIO1: 4-7
        # HOWEVER: PIO1 SM0+SM1 are used for WiFi (sm_index 4-5)!!!
        if self.pio_block_index == 1 and self.mode == MODE_COUNTED:
            raise ConfigurationException(f"Cannot operate step motor in counted mode (e.g. ballfeeder) on PIO block 1, as this is partly occupied by WLAN. Change motor config to use pio block 0!")
        if self.debug:
            print(f"{base_sm_index=})")
        prg_name = ''
        try:
            if self.mode == MODE_COUNTED:
                prg_name = 'irq'
                rp2.PIO(self.pio_block_index).irq(self._irq_handler)
                prg_name = 'counter_sm'
                self._counter_sm = rp2.StateMachine(base_sm_index + 0, trigger_steps, freq=counter_freq) # controls the sequences
                prg_name = 'runner_fwd_sm (counted)'
                self._runner_fwd_sm = rp2.StateMachine(base_sm_index + 1, run_forward_pio, freq=runner_freq, set_base=self.pins[0]) # performs the steps for a forward sequence
                prg_name = 'runner_bwd_sm (counted)'
                self._runner_bwd_sm = rp2.StateMachine(base_sm_index + 2, run_backward_pio, freq=runner_freq, set_base=self.pins[0]) # performs the steps for a backward sequence
            elif self.mode == MODE_PERMANENT:
                prg_name = 'runner_fwd_sm (permanent)'
                # here we use offset 3, so that it is possible to have 1 feeder and 1 stirrer in the same PIO block
                self._runner_fwd_sm = rp2.StateMachine(base_sm_index + 3, run_endless_pio, freq=runner_freq, set_base=self.pins[0]) # performs the steps for a forward sequence
            elif self.mode != MODE_UNSET:
                raise Exception(f"Invalid mode specified: {self.mode}")
        except Exception as e:
            if self.debug:
                print(f"Could not create PIO program ({prg_name}): {str(e)}")
            raise e
        if self.debug:
            print(f"Created statemachines for {self.mode=} in PIO block {self.pio_block_index}.")

    # def _create_statemachines(self, mode: int, runner_freq = 20000, counter_freq = 2000):
    #     """mode:              mode of operation: MODE_FEEDER, MODE_PERMANENT, MODE_INTERVAL
    #        runner_freq:       The frequency (Hz) to operate the state machines for driving the motor forward/backward.
    #        counter_freq:      The frequency (Hz) to operate the state machine for controlling the number of motor steps.
    #     """
    #     if self.debug:
    #         print(f"_create_statemachines({mode=}, {runner_freq=}, {counter_freq=})")
    #     try:
    #         rp2.PIO(self.pio_block_index).remove_program() # clear all programs from PIO block
    #     except Exception as e:
    #         if self.debug:
    #             print(f"Could not remove PIO programs: {str(e)}")
    #     # This whole dynamic handling is no longer required, as there are basically just two modes of operation to distinguish:
    #     # - run endlessly in either direction or
    #     # - run for specific time in either direction (meaning there steps are counted and callback is possible)
    #     self._counter_sm = None
    #     self._runner_fwd_sm = None
    #     self._runner_bwd_sm = None
    #     base_sm_index = self.pio_block_index * 4 # PIO0: 0-3; PIO1: 4-7
    #     # HOWEVER: PIO1 SM0+SM1 are used for WiFi (sm_index 4-5)!!!
    #     if base_sm_index > 3 and base_sm_index < 6:
    #         if mode == MODE_COUNTED:
    #             raise ConfigurationException(f"Cannot operate step motor in counted mode (e.g. ballfeeder) on PIO block 1, as this is partly occupied by WLAN. Change config to use block 0 and use block 1 only for permanent operation (e.g. stirrers).")
    #         base_sm_index = 6
    #     if self.debug:
    #         print(f"{base_sm_index=})")
    #     prg_name = ''
    #     try:
    #         if mode == MODE_COUNTED:
    #             prg_name = 'irq'
    #             rp2.PIO(self.pio_block_index).irq(self._irq_handler)
    #             prg_name = 'counter_sm'
    #             self._counter_sm = rp2.StateMachine(base_sm_index + 0, trigger_steps, freq=counter_freq) # controls the sequences
    #             prg_name = 'runner_fwd_sm (counted)'
    #             self._runner_fwd_sm = rp2.StateMachine(base_sm_index + 1, run_forward_pio, freq=runner_freq, set_base=self.pins[0]) # performs the steps for a forward sequence
    #             prg_name = 'runner_bwd_sm (counted)'
    #             self._runner_bwd_sm = rp2.StateMachine(base_sm_index + 2, run_backward_pio, freq=runner_freq, set_base=self.pins[0]) # performs the steps for a backward sequence
    #         elif mode == MODE_PERMANENT:
    #             # self._counter_sm = rp2.StateMachine(base_prg_index + 0, trigger_steps_endless, freq=counter_freq) # controls the sequences
    #             # self._runner_fwd_sm = rp2.StateMachine(base_prg_index + 1, run_forward_pio, freq=runner_freq, set_base=self.pins[0]) # performs the steps for a forward sequence
    #             # self._runner_bwd_sm = rp2.StateMachine(base_prg_index + 2, run_backward_pio, freq=runner_freq, set_base=self.pins[0]) # performs the steps for a backward sequence
    #             prg_name = 'runner_fwd_sm (permanent)'
    #             self._runner_fwd_sm = rp2.StateMachine(base_sm_index + 0, run_endless_pio, freq=runner_freq, set_base=self.pins[0]) # performs the steps for a forward sequence
    #         elif mode != MODE_UNSET:
    #             raise Exception(f"Invalid mode specified: {mode}")
    #     except Exception as e:
    #         if self.debug:
    #             print(f"Could not create PIO program ({prg_name}): {str(e)}")
    #         raise e
    #     self.mode = mode
    #     if self.debug:
    #         print(f"Created statemachines for {self.mode=} in PIO block {self.pio_block_index}.")

    def rotate(self, speed_rpm: float = 1.0):
        """Endlessly turns the motor with the specified speed.
           The direction is dependent on the sign of speed_rpm:
           
           Parameters:
           speed_rpm (float): The speed in rotations per minute. Positive value means forward, negative means backwards. Passing 0 will result in no effect at all.
        """
        # Empiric:
        # 1 round per 5 sec equals 20kHz
        # 0.2 rps <=> 20 kHz
        # 0.2 Hz <=> 20000 Hz
        # 1 <=> 100000
        if self.debug:
            print(f"run_forever({speed_rpm=}) called")
        if self.mode != MODE_PERMANENT:
            raise Exception("rotate() is only allowed in continuous mode!")

        if speed_rpm == 0.0:
            return
        if self._operating:
            raise Exception("Ongoing Rotation not yet finished!")
        self._operating = True
        
        try:
            if speed_rpm < 0.0:
                self._current_direction = -1
                speed_rpm = -speed_rpm
            else:
                self._current_direction = 1

            # Unfortunately, this formula doesn't make any sense. However, it gives a suitable result
            freq = ceil(speed_rpm * TICKS_PER_CYCLE * self.full_rotation_steps) # steps per sec

            if self.debug:
                print(f"{freq=}")
            if freq > self.runner_freq:
                freq = self.runner_freq
                if self.debug:
                    print(f"Frequency is capped at {freq} Hz")
            elif freq < SM_MIN_FREQ:
                freq = SM_MIN_FREQ
                if self.debug:
                    print(f"Frequency is raised to lower limit of {freq} Hz")

            # set up the state machines (freq might have changed)
            self.v2_create_statemachines(runner_freq=freq)

            # activate only the fwd sm
            if self._runner_fwd_sm:
                self._runner_fwd_sm.active(1)
            #self._set_direction(self._current_direction)
            if self.debug:
                print(f"Endless operation started ({freq=}, {self._current_direction=}).")
        except Exception as e:
            print(f"Error: {e}")
            self._set_direction(0)
            raise e

    # def rotate(self, speed_rpm: float):
    #     """Endlessly turns the motor with the specified speed.
    #        The direction is dependent on the sign of speed_rpm:
           
    #        Parameters:
    #        speed_rpm (float): The speed in rotations per minute. Positive value means forward, negative means backwards. Passing 0 will result in no effect at all.
    #     """
    #     # Empiric:
    #     # 1 round per 5 sec equals 20kHz
    #     # 0.2 rps <=> 20 kHz
    #     # 0.2 Hz <=> 20000 Hz
    #     # 1 <=> 100000
    #     if self.debug:
    #         print(f"rotate({speed_rpm=}) called")
    #     if speed_rpm == 0.0:
    #         return
    #     if self._operating:
    #         raise Exception("Ongoing Rotation not yet finished!")
    #     self._operating = True
        
    #     try:
    #         if speed_rpm < 0.0:
    #             self._current_direction = -1
    #             speed_rpm = -speed_rpm
    #         else:
    #             self._current_direction = 1

    #         # Unfortunately, this formula doesn't make any sense. However, it gives a suitable result
    #         freq = ceil(speed_rpm * TICKS_PER_CYCLE * self.full_rotation_steps) # steps per sec

    #         if self.debug:
    #             print(f"{freq=}")
    #         if freq > self.runner_freq:
    #             freq = self.runner_freq
    #             if self.debug:
    #                 print(f"Frequency is capped at {freq} Hz")
    #         elif freq < SM_MIN_FREQ:
    #             freq = SM_MIN_FREQ
    #             if self.debug:
    #                 print(f"Frequency is raised to lower limit of {freq} Hz")

    #         # self._create_statemachines(MODE_PERMANENT, runner_freq=freq)
    #         # self._set_direction(self._current_direction)
    #         if self.debug:
    #             print(f"Endless operation started ({freq=}, {self._current_direction=}).")
    #     except Exception as e:
    #         print(f"Error: {e}")
    #         self._set_direction(0)
    #         raise e

    def rotate_by_angle(self, angle: float, op_complete_callback=None):
        """Turns the motor by the specified angle (speed not adjustable).
           The direction is dependent on the sign of angle:
           Positive means forward, negative means backwards
           
           Parameters:
           angle (float): The amount of degrees to turn. Passing 0 will result in no effect at all.
           op_complete_callback: Reference onto a 1-parameter function for callback when the operation is finished. The parameter will hold the reference onto the motor object.
        """
        if self.debug:
            print(f"rotate_by_angle() called: {angle} degrees...")
        if self.mode != MODE_COUNTED:
            raise Exception("run_forever() is only allowed in counted mode!")
        if angle == 0:
            return
        if self._operating:
            raise Exception("Ongoing Rotation not yet finished!")
        self._op_complete_callback = op_complete_callback
        self._operating = True
        try:
            steps_to_rotate = round(angle / self.angle_per_step)

            if self.debug:
                print(f"steps to do: {steps_to_rotate}")
            #print(f"wait between steps: {self.waitTimeMs} ms")
            if steps_to_rotate < 0:
                self._current_direction = -1
                steps_to_rotate = abs(steps_to_rotate)
            else:
                self._current_direction = 1

            # set up the state machines
            self.v2_create_statemachines()
            self._set_direction(self._current_direction)
            self._counter_sm.put(steps_to_rotate) # this starts the action
            if self.debug:
                print(f"Operation started ({steps_to_rotate=}, {self._current_direction=}).")
        except Exception as e:
            print(f"Error: {e}")
            self._set_direction(0)
            raise e

    # def rotate_by_angle(self, angle: float, op_complete_callback=None):
    #     """Turns the motor by the specified angle (speed not adjustable).
    #        The direction is dependent on the sign of angle:
    #        Positive means forward, negative means backwards
           
    #        Parameters:
    #        angle (float): The amount of degrees to turn. Passing 0 will result in no effect at all.
    #        op_complete_callback: Reference onto a 1-parameter function for callback when the operation is finished. The parameter will hold the reference onto the motor object.
    #     """
    #     if self.debug:
    #         print(f"rotate_by_angle() called: {angle} degrees...")
    #     if angle == 0:
    #         return
    #     if self._operating:
    #         raise Exception("Ongoing Rotation not yet finished!")
    #     self._op_complete_callback = op_complete_callback
    #     self._operating = True
    #     try:
    #         steps_to_rotate = round(angle / self.angle_per_step)

    #         if self.debug:
    #             print(f"steps to do: {steps_to_rotate}")
    #         #print(f"wait between steps: {self.waitTimeMs} ms")
    #         if steps_to_rotate < 0:
    #             self._current_direction = -1
    #             steps_to_rotate = abs(steps_to_rotate)
    #         else:
    #             self._current_direction = 1

    #         # set up the state machines
    #         self._create_statemachines(MODE_COUNTED)
    #         self._set_direction(self._current_direction)
    #         self._counter_sm.put(steps_to_rotate) # this starts the action
    #         if self.debug:
    #             print(f"Operation started ({steps_to_rotate=}, {self._current_direction=}).")
    #     except Exception as e:
    #         print(f"Error: {e}")
    #         self._set_direction(0)
    #         raise e

    def _set_direction(self, direction = 0):
        """Sets the movement direction by activating the according statemachines."""
        if self.debug:
            print(f"Setting direction to {direction} in PIO block {self.pio_block_index}")
        if direction > 0:
            if self._runner_bwd_sm:
                self._runner_bwd_sm.active(0)
            if self._runner_fwd_sm:
                self._runner_fwd_sm.active(1)
            if self._counter_sm:
                self._counter_sm.active(1)
        elif direction < 0:
            if self._runner_fwd_sm:
                self._runner_fwd_sm.active(0)
            if self._runner_bwd_sm:
                self._runner_bwd_sm.active(1)
            if self._counter_sm:
                self._counter_sm.active(1)
        else:
            if self._counter_sm: 
                self._counter_sm.active(0)
            if self._runner_fwd_sm:
                self._runner_fwd_sm.active(0)
            if self._runner_bwd_sm:
                self._runner_bwd_sm.active(0)
            self._operating = False

    def stop(self) -> None:
        """Brings the motor to an immediate halt by deactivating the stepper SMs"""
        self._set_direction(0)
        self._op_complete_callback = None
        self._operating = False

    def _irq_handler(self, pio):
        """Handle the interrupt from the step counter SM if the operation is complete."""
        if self.debug:
            print(f"Operation completed. {pio=}")
        self._operating = False
        self._set_direction(0) # deactivate SMs
        if self._op_complete_callback:
            self._op_complete_callback(self)

    def getStatusData(self) -> dict:
        return {
            'mode': self.mode,
            'current_direction': self._current_direction,
            'operating': self._operating,
        }
    def getConfigData(self) -> dict:
        return {
            'type': type(self).__name__,
            'starting_gp_pin': self.starting_gp_pin ,
            'consecutive_pins': self.consecutive_pins,
            'gear_ratio': self.gear_ratio,
            'inner_motor_steps': self.inner_motor_steps,
            'correction_steps': self.correction_steps,
            'runner_freq': self.runner_freq,
            'counter_freq': self.counter_freq,
            'pio_block_index': self.pio_block_index,
        }
    def setConfigData(self, data: dict) -> dict:
        if self.debug:
            print(f"{__class__.__name__}setConfigData({data=})")
        tmp = data.get('starting_gp_pin')
        if tmp is not None:
            self.starting_gp_pin  = int(tmp)
        tmp = data.get('consecutive_pins')
        if tmp is not None:
            self.consecutive_pins = int(tmp)
        tmp = data.get('gear_ratio')
        if tmp is not None:
            self.gear_ratio = int(tmp)
        tmp = data.get('inner_motor_steps')
        if tmp is not None:
            self.inner_motor_steps = int(tmp)
        tmp = data.get('correction_steps')
        if tmp is not None:
            self.correction_steps = int(tmp)
        tmp = data.get('runner_freq')
        if tmp is not None:
            self.runner_freq = int(tmp)
        tmp = data.get('counter_freq')
        if tmp is not None:
            self.counter_freq = int(tmp)
        tmp = data.get('pio_block_index')
        if tmp is not None:
            self.pio_block_index = int(tmp)
        self.adopt_config()
        return self.getConfigData()

import rp2
@rp2.asm_pio(set_init=rp2.PIO.OUT_LOW)
def trigger_steps_endless():
    # triggers steps conditionless, i.e. motor runs endlessly
    irq(block, rel(6))      # trigger step and wait
    wrap()

@rp2.asm_pio(set_init=rp2.PIO.OUT_LOW)
def trigger_steps():
    # Counts the steps backwards, triggering execution via IRQ6 and raises IRQ0 if reaching step#0.
    # Number of steps must be put into TX FIFO before
    pull(block)             # read the number of steps into OSR (blocking until value is available)
    mov(x, osr)             # store number of steps into X
    label("next_step")
    irq(block, rel(6))      # trigger step and wait
    jmp(x_dec, "next_step") # decrease X and repeat if still >0
    irq(rel(0))             # signal that requested operation is finished
    wrap()

@rp2.asm_pio(set_init=(rp2.PIO.OUT_LOW, rp2.PIO.OUT_LOW, rp2.PIO.OUT_LOW, rp2.PIO.OUT_LOW))
def run_endless_pio():
    #[1,0,0,0],[1,1,0,0],[0,1,0,0],[0,1,1,0],[0,0,1,0],[0,0,1,1],[0,0,0,1],[1,0,0,1]
    #duration(delay=23): 192 (TICKS_PER_CYCLE)
    delay = 23
    #wait(1, irq, rel(5)) # wait for the trigger-irq
    set(pins, 8) [delay]  # 0b1000
    set(pins, 12)[delay]  # 0b1100
    set(pins, 4) [delay]  # 0b0100
    set(pins, 6) [delay]  # 0b0110
    set(pins, 2) [delay]  # 0b0010
    set(pins, 3) [delay]  # 0b0011
    set(pins, 1) [delay]  # 0b0001
    set(pins, 9) [delay]  # 0b1001
    wrap()

@rp2.asm_pio(set_init=(rp2.PIO.OUT_LOW, rp2.PIO.OUT_LOW, rp2.PIO.OUT_LOW, rp2.PIO.OUT_LOW))
def run_forward_pio():
    #[1,0,0,0],[1,1,0,0],[0,1,0,0],[0,1,1,0],[0,0,1,0],[0,0,1,1],[0,0,0,1],[1,0,0,1]
    #duration(delay=23): 192 (TICKS_PER_CYCLE)
    delay = 23
    wait(1, irq, rel(5)) # wait for the trigger-irq
    set(pins, 8) [delay]  # 0b1000
    set(pins, 12)[delay]  # 0b1100
    set(pins, 4) [delay]  # 0b0100
    set(pins, 6) [delay]  # 0b0110
    set(pins, 2) [delay]  # 0b0010
    set(pins, 3) [delay]  # 0b0011
    set(pins, 1) [delay]  # 0b0001
    set(pins, 9) [delay]  # 0b1001
    wrap()
   
@rp2.asm_pio(set_init=(rp2.PIO.OUT_LOW, rp2.PIO.OUT_LOW, rp2.PIO.OUT_LOW, rp2.PIO.OUT_LOW))
def run_backward_pio():
    # basically reverse of [1,0,0,0],[1,1,0,0],[0,1,0,0],[0,1,1,0],[0,0,1,0],[0,0,1,1],[0,0,0,1],[1,0,0,1]
    #duration(delay=23): 192 (TICKS_PER_CYCLE)
    delay = 23
    wait(1, irq, rel(4)) # wait for the trigger-irq
    set(pins, 1) [delay]  # 0b0001
    set(pins, 3) [delay]  # 0b0011
    set(pins, 2) [delay]  # 0b0010
    set(pins, 6) [delay]  # 0b0110
    set(pins, 4) [delay]  # 0b0100
    set(pins, 12)[delay]  # 0b1100
    set(pins, 8) [delay]  # 0b1000
    set(pins, 9) [delay]  # 0b1001
    wrap()

def run_endless_test(mot: StepMotorPIO, duration=10, speed=1, dir=1):
    """This tests runs the motor permanently for the specified time.
    """
    mot.rotate(speed)
    time.sleep(duration)
    mot.stop()
    print(f"Endless test finished.")

def run_translation_test(mot: StepMotorPIO, repeats=1, dir=1):
    """This tests runs a specified amount of full-turns.
    After it is finished, the motor position should be exactly the same as in the beginning.
    The higher the number of repeats, the more deviation will derive from a small error.
    The resulting deviation can be used to correct the motor's AnglePerStep value.
    """
    angle = 360
    while repeats > 0:
        mot.rotate_by_angle(angle*dir, 4)
        while mot._operating:
            time.sleep(.1)
        repeats -= 1
        print(f"{repeats/2} left...")

def run_alternation_test(mot: StepMotorPIO, angle=360.0, repeats=1):
    """This tests runs a specified amount of alternating forward/backward turns by the specified number of degrees.
    """
    repeats = 2*repeats # one repeat is actually once forth and once back
    # call the first operation and provide the callback for the next one
    mot.rotate_by_angle(angle, op_complete_callback=lambda mot, r=repeats, a=angle: reverse_direction(mot, r, a))
    while mot._operating:
        time.sleep(.1) # block until done

def reverse_direction(mot: StepMotorPIO, current_repeats: int, angle: float):
    print(f"Callback successful ({current_repeats=}, {angle=}). Is now used to initiate the next operation in reverse direction.")
    current_repeats -= 1 # decrement the iteration counter
    if current_repeats > 0:
        angle = -angle       # reverse direction
        if current_repeats % 2 == 0:
            print(f"{current_repeats/2} left...")
        # call the first operation and provide the callback for the next one
        mot.rotate_by_angle(angle, op_complete_callback=lambda mot, r=current_repeats, a=angle: reverse_direction(mot, r, a))
    else:
        print("Final callback reached.")

if __name__ == "__main__":
    mot = StepMotorPIO(MODE_COUNTED)
    try:
        t0 = time.ticks_us()
        #run_endless_test(mot, 10, 15)
        run_alternation_test(mot, angle=110, repeats=1)
        #runTranslationTest(mot, repeats=0)
        t1 = time.ticks_us()
        print(f"Duration: {(t1-t0)/1000000} s")
    except Exception:
        print("termination requested - please wait...")
    finally:
        mot.stop()
        print("terminated.")

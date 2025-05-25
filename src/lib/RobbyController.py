# Copyright (c) 2024 Reiner Nikulski
# 
# This software is released under the MIT License.
# https://opensource.org/licenses/MIT
robby_version = "0.1.0"
import sys
if 'micropython' not in sys.version.lower():
    from typing import List, Union
from BallFeeder import BallFeeder
from BallStirrer import BallStirrer
from MachineRotator import MachineRotator
from sg92r import Sg92r
from _thread import start_new_thread, allocate_lock
import gc
import json
from machine import Timer
from utime import sleep, sleep_ms
from BallDriver import BallDriver
from API import API
from RobbyExceptions import *
from RobbySettings import RobbySettings
from Shot import Shot
from ShotCycle import ShotCycle
from StepMotorPIO import StepMotorPIO, MODE_COUNTED, MODE_PERMANENT
import WebServer

# Machine mode
MODE_TEXTS = {0: 'Continuous', 1: 'Program', 2: 'Configuration'}
MODE_CONTINUOUS = 0
MODE_PROGRAM = 1
MODE_CONFIGURATION = 2
# Machine operation status
STATUS_TEXTS = {0: 'Idle', 1: 'Preparing', 2: 'Playing', 3: 'Paused', 9: 'Stopping...', 99: 'Error! Reset required.'}
STATUS_IDLE = 0
"""No operation started - doing nothing"""
STATUS_PREPARING = 1
"""Preparing to start operation"""
STATUS_PLAYING = 2
"""Playing shots"""
STATUS_PAUSED = 3
"""Operation is paused."""
STATUS_STOPPING = 9
"""Halting operation"""
STATUS_ERROR = 99
"""An error occurred. Device needs to be reset!"""
# Dict keys
KEY_GENERAL_SETTINGS = 'general'
KEY_BALL_DRIVERS = 'balldrivers'
KEY_BALL_FEEDERS = 'ballfeeders'
KEY_BALL_STIRRERS = 'ballstirrers'
KEY_MACHINE_ROTATORS = 'machinerotators'

class RobbyController:
    lock_mode = allocate_lock()
    lock_status = allocate_lock()
    total_mem = gc.mem_free()+gc.mem_alloc()

    """Class used to control the high-level functions of the whole roboter"""
    BALL_PUSHER_DURATION = 1.25
    """Duration in seconds the machine needs to perform one full cycle, from releasing one ball to the next one

    Too fast operation will cause the stepper motor to move unreliably or not to move at all.
    """
    BALL_RELEASE_DURATION = 0.25 
    """Pause time after ball feeder starts operating (pushing the ball into the driver) and before the driver-motor settings for the next shot are initiated.  

    Shall prevent the robo parts from being moved too early, before the ball has been released completely.
    """
    MAX_BALL_FREQUENCY = 1 / BALL_PUSHER_DURATION

    def __init__(self, config_path: str='/ttrobby-config.json', no_server: bool=False, debug=False) -> None:
        """Parameters:
           settings_path: path to the settings file
           no_server: set to True to prevent webserver from starting
           debug: enable verbose output
        """
        print("------------------------------------------------------")
        print(r"  ______ _______      _____       _     _           ")
        print(r" |__   _|__   __|    |  __ \     | |   | |          ")
        print(r"    | |    | |  ___  | |__) |___ | |__ | |__  _   _ ")
        print(r"    | |    | | |___| |  _  // _ \| '_ \| '_ \| | | |")
        print(r"    | |    | |       | | \ \ (_) | |_) | |_) | |_| |")
        print(r"    |_|    |_|       |_|  \_\___/|_.__/|_.__/ \__, |")
        print(r"                                               __/ |")
        print(r"                                              |___/ ")
        print(f"RobbyController v{robby_version}, 2025")
        print("------------------------------------------------------")

        try:
            txt_step = "Init Class"
            self.debug = debug
            if self.debug:
                print("Initializing RobbyController: ", txt_step)
            self.errors = []
            self.API = API(self, debug)
            self._mode = MODE_CONFIGURATION
            self._mode_requested = MODE_CONFIGURATION
            self._status = STATUS_IDLE
            self._status_requested = STATUS_IDLE

            txt_step = "Load Settings"
            if self.debug:
                print("Initializing RobbyController: ", txt_step)
            self.config_path = config_path
            settings = self._load_settings(config_path)
            self.__general_settings = RobbySettings()
            self.adopt_general_settings(settings[KEY_GENERAL_SETTINGS])

            txt_step = "WebServer Initialization"
            self.webserver = None
            if self.debug:
                print("Initializing RobbyController: ", txt_step)
            if self.__general_settings.net_webserver_autostart and not no_server:
                # start webserver in separate thread
                self.webserver = WebServer.WebServer(port=self.__general_settings.net_webserver_port)
                self.webserver_thread = start_new_thread(self.webserver.run, (self, ))

            txt_step = "BallDriver Initialization"
            if self.debug:
                print(f"{self.webserver=}")
                print("Initializing RobbyController: ", txt_step)
            self.ballDrivers: List[BallDriver] = []
            if KEY_BALL_DRIVERS in settings:
                for cfg in settings[KEY_BALL_DRIVERS]:
                    if cfg['motor_driver']['type'] == 'PCA9685':
                        try:
                            self.ballDrivers.append(BallDriver(bd_number=cfg['bd_number'], motor_angles=cfg['motor_angles'], i2c_channel=cfg['motor_driver']['i2c_channel'], sda_pin=cfg['motor_driver']['sda_pin'], address=cfg['motor_driver']['address'], debug=self.debug))
                            for motor in cfg['motors']:
                                self.ballDrivers[-1].motors[motor['motor_number']].polarity = motor['polarity']
                        except Exception as e:
                            self.errors.append(f"ERROR: Could not instantiate ball driver: {str(e)}")
                            print(self.errors[-1])
                    else:
                        raise NotImplementedError(f"Motor Driver class '{cfg['motor_driver']['type']}' has not been implemented yet!")
            else:
                self.ballDrivers.append(BallDriver(0, debug=self.debug))

            txt_step = "Ball Feeders Initialization"
            if self.debug:
                print(f"{self.ballDrivers=}")
                print("Initializing RobbyController: ", txt_step)
            self.ball_feeders: List[BallFeeder] = []
            if KEY_BALL_FEEDERS in settings:
                for mot_cfg in settings[KEY_BALL_FEEDERS]:
                    cfg = mot_cfg['config']
                    if mot_cfg['type'] == 'StepMotorPIO':
                        motor = StepMotorPIO(mode=MODE_COUNTED, starting_gp_pin=cfg['starting_gp_pin'], consecutive_pins=cfg['consecutive_pins'], pio_block_index=cfg['pio_block_index'], debug=self.debug)
                        motor.inner_motor_steps = cfg['inner_motor_steps']
                        motor.gear_ratio = cfg['gear_ratio']
                        motor.runner_freq = cfg['runner_freq']
                        motor.correction_steps = cfg['correction_steps']
                        motor.counter_freq = cfg['counter_freq']
                    else:
                        raise NotImplementedError(f"Motor class '{mot_cfg['type']}' has not been implemented yet to be loaded from config!")
                    feeder = BallFeeder(motor=motor, debug=self.debug)
                    self.ball_feeders.append(feeder)
            else:
                # create one default entry
                self.ball_feeders.append(BallFeeder(motor=StepMotorPIO(mode=MODE_COUNTED, starting_gp_pin=2, pio_block_index=0, debug=self.debug), debug=self.debug))

            txt_step = "Ball Stirrers Initialization"
            if self.debug:
                print(f"{self.ball_feeders=}")
                print("Initializing RobbyController: ", txt_step)
            self.ball_stirrers: List[BallStirrer] = []
            if KEY_BALL_STIRRERS in settings:
                for cfg_mot in settings[KEY_BALL_STIRRERS]:
                    cfg = cfg_mot['config']
                    if cfg_mot['type'] == 'StepMotorPIO':
                        motor = StepMotorPIO(mode=MODE_PERMANENT, starting_gp_pin=cfg['starting_gp_pin'], consecutive_pins=cfg['consecutive_pins'], pio_block_index=cfg['pio_block_index'], debug=self.debug)
                        motor.inner_motor_steps = cfg['inner_motor_steps']
                        motor.gear_ratio = cfg['gear_ratio']
                        motor.runner_freq = cfg['runner_freq']
                        motor.correction_steps = cfg['correction_steps']
                        motor.counter_freq = cfg['counter_freq']
                    elif cfg_mot['type'] == 'Sg92r':
                        motor = Sg92r(debug=self.debug)
                        motor.setConfigData(cfg)
                    stirrer = BallStirrer(motor, debug=self.debug)
                    self.ball_stirrers.append(stirrer)
            else:
                # create one default entry
                self.ball_stirrers.append(BallStirrer(motor=StepMotorPIO(mode=MODE_PERMANENT, starting_gp_pin=10, pio_block_index=1, debug=self.debug), debug=self.debug))
            
            txt_step = "Machine Rotators Initialization"
            if self.debug:
                print(f"{self.ball_stirrers=}")
                print("Initializing RobbyController: ", txt_step)
            self.machine_rotators: List[MachineRotator] = []
            if KEY_MACHINE_ROTATORS in settings:
                for cfg_rot in settings[KEY_MACHINE_ROTATORS]:
                    rotator = MachineRotator(debug=self.debug)
                    rotator.setConfigData(cfg_rot)
            else:
                # create one default entry
                self.machine_rotators.append(MachineRotator(debug=self.debug))

            txt_step = "BallTimer Initialization"
            if self.debug:
                print("Initializing RobbyController: ", txt_step)
            self.BallTimer = Timer() # type: ignore
            self.BallTimerRunning = False
            self.current_ballfeeder_cycle_index = -1
            """Current index in the ballfeeder cycle. Is -1 if in the waiting position."""
            
            txt_step = "ShotCycle Initialization"
            if self.debug:
                print("Initializing RobbyController: ", txt_step)
            self.ShotCycle = ShotCycle([Shot.get_default_shot_from_settings(self.__general_settings)])

            txt_step = "ContinuousShot Initialization"
            if self.debug:
                print("Initializing RobbyController: ", txt_step)
            self.ContinuousShot = Shot.get_default_shot_from_settings(self.__general_settings)

        except Exception as e:
            self.errors.append(f"Error during {txt_step}: {e}") 
            print(self.errors[-1])
            self._status = STATUS_ERROR
            #raise e
        finally:
            print("Free memory: ", gc.mem_free(), "/", self.total_mem)
    
    def adopt_general_settings(self, settings: dict):
        """Take over any changes in the settings. Machine must be in configuration mode!"""
        if self._mode != MODE_CONFIGURATION:
            raise InvalidOperationException("Machine must be in configuration mode to update the config.")
        try:
            txt_step = "Update Settings Object"
            self.__general_settings.load_from_config(settings)
            txt_step = "Device Initialization"
            WebServer.WebServer.setHostname(self.__general_settings.net_hostname)
            txt_step = "General Initialization"
            self.ball_feeder_cycle = self.__general_settings.BallFeederCycle # motor steps to go; pausing after the last step until the next ball is triggered; the sum must be zero!!
            self.ball_feeder_current_step = -1
        except Exception as e:
            print(f"Error during adopting settings, step {txt_step}: {e}")
            raise e

    def run(self):
        """Method to keep the controller in memory (endless loop until exception occurs)."""
        sleeptime_ms = 100
        mem_interval_ms = 10 * 1000
        mem_interval_left = 0
        while True:
            if self._status != self._status_requested:
                # State transition: * --> IDLE
                if self._status_requested == STATUS_IDLE:
                    #TODO: Check if _stop_playing() is still necessary in its synchronous form or if it can be used for this:
                    # Stop routines only execute once
                    if self._status != STATUS_STOPPING:
                        self._status = STATUS_STOPPING
                        self._stop_balldrivers()
                        self._stop_stirrers()
                        if self.BallTimerRunning:
                            self.BallTimerRunning = False
                            self.BallTimer.deinit()
                        self.ShotCycle.reset()
                    # the ball feeders will stop when reaching the waiting position, then we can update the status:
                    if self.current_ballfeeder_cycle_index == -1:
                        self._status = self._status_requested

                # State transition: * --> PAUSED
                if self._status_requested == STATUS_PAUSED:
                    if self.BallTimerRunning:
                        self.BallTimerRunning = False
                        self.BallTimer.deinit()
                    # the ball feeders will stop when reaching the waiting position, then we update the status:
                    if self.current_ballfeeder_cycle_index == -1:
                        self._status = self._status_requested

                # State transition: * --> PLAYING
                if self._status_requested == STATUS_PLAYING:
                    if self._status != STATUS_PREPARING:
                        # Start the engines
                        self._status = STATUS_PREPARING
                        self._start_balldrivers()
                        self._start_stirrers()
                    # the ball feeders should be in the waiting position, then we can update the status:
                    if self.current_ballfeeder_cycle_index == -1:
                        self._status = self._status_requested
                        self._start_playing_async()


            if self._mode != self._mode_requested:
                self.lock_mode.acquire()
                self._mode = self._mode_requested
                self.lock_mode.release()
                # try:
                #     if self._mode == MODE_CONTINUOUS:
                #         if self._mode_requested == MODE_PROGRAM:
                #             self._start_playing()
                #     elif self._mode == MODE_CONFIGURATION:
                #         if self._mode_requested == MODE_PROGRAM:
                #             self._start_playing()
                #     elif self._mode == MODE_PROGRAM:
                #         if self._mode_requested == MODE_CONTINUOUS or self._mode_requested == MODE_CONTINUOUS:
                #             self._stop_playing()

                #     self.mode = self._mode_requested
                #     self.lock_mode.release()
                # except Exception as e:
                #     self.lock_mode.release()
                #     raise Exception(f"Error during mode traversion: {str(e)}")

            sleep_ms(sleeptime_ms)
            if mem_interval_left > 0:
                mem_interval_left -= sleeptime_ms
            else:
                mem_interval_left = mem_interval_ms
                print("Free memory: ", gc.mem_free(), "/", self.total_mem)

    def _load_settings(self, path: str='') -> dict:
        try:
            if path == '':
                path = self.config_path
            if self.debug:
                print(f"Loading settings from file '{path}'.")
            with open(path,'r') as f:
                settings = json.load(f)
            if not settings:
                return {}
            return settings
        except Exception as e:
            raise Exception(f"Cannot load settings from file '{path}': {str(e)}")
        
    def _save_settings(self, path: str=''):
        try:
            if path == '':
                path = self.config_path
            if self.debug:
                print(f"Saving settings to file '{path}'.")
            settings = {
                KEY_GENERAL_SETTINGS: self.__general_settings.getConfigData(),
                KEY_BALL_DRIVERS: [bd.getConfigData() for bd in self.ballDrivers],
                KEY_BALL_FEEDERS: [bf.getConfigData() for bf in self.ball_feeders],
                KEY_BALL_STIRRERS: [bs.getConfigData() for bs in self.ball_stirrers],
                }
            with open(path,'w') as f:
                settings = json.dump(settings, f)
        except Exception as e:
            Exception(f"Cannot save settings to file '{path}': {str(e)}")

    def _start_stirrers(self) -> None:
        i = 0
        for stirrer in self.ball_stirrers:
            try:
                stirrer.start()
                i += 1
            except Exception as e:
                print(f"Error starting stirrer {i}: {e}")
        if self.debug:
            print(f"{i} stirrers started.")

    def _stop_stirrers(self) -> None:
        i = 0
        for stirrer in self.ball_stirrers:
            try:
                stirrer.stop()
                i += 1
            except Exception as e:
                print(f"Error stopping stirrer {i}: {e}")
        if self.debug:
            print(f"{i} stirrers successfully stopped.")
    
    def _start_balldrivers(self) -> None:
        i = 0 # currently we have only one!
        try:
            self.set_ball_acceleration(i, self.__general_settings.default_ball_speed, self.__general_settings.default_topspin, self.__general_settings.default_sidespin)
            i += 1
        except Exception as e:
            print(f"Error starting balldriver {i}: {e}")
        if self.debug:
            print(f"{i} balldrivers started.")

    def _stop_balldrivers(self) -> None:
        i = 0 # currently we have only one!
        for bd in self.ballDrivers:
            try:
                bd.stop()
                i += 1
            except Exception as e:
                print(f"Error stopping balldriver {i}: {e}")
        if self.debug:
            print(f"{i} balldrivers successfully stopped.")

    def _stop_feeders(self) -> None:
        i = 0
        for stepmotor in self.ball_feeders:
            try:
                stepmotor.stop()
                i += 1
            except Exception as e:
                print(f"Error stopping ball feeder {i}: {e}")
        if self.debug:
            print(f"{i} ball feeders successfully stopped.")

    def _ball_feeder_prepare_after_mount(self) -> None:
        """Move the ball feeder into waiting position."""
        # Waiting position is after the last step of the ball feeder cycle. 
        if self.current_ballfeeder_cycle_index >= 0:
            raise ImplementationException("Ball Feeder is currently operating and cannot be moved into the waiting position!")
        if self.debug:
            print(f"Ball Feeder preparing after mount")
        if self.__general_settings.BallFeederMountIndex >= len(self.ball_feeder_cycle) - 1:
            # nothing to do (already in waiting position)
            return
        self.current_ballfeeder_cycle_index = self.__general_settings.BallFeederMountIndex + 1 # perform the next step
        for mot in self.ball_feeders:
            mot.motor.rotate_by_angle(angle=self.ball_feeder_cycle[self.current_ballfeeder_cycle_index], op_complete_callback=self._ball_feeder_next_step)

    def _release_next_ball(self) -> None:
        """Trigger the feeder cycle for the next ball"""
        if self.current_ballfeeder_cycle_index >= 0:
            raise ImplementationException("Ball Feeder not finished with previous operation.")
        if self.debug:
            print(f"Ball Feeder releasing next ball")
        self.current_ballfeeder_cycle_index = 0
        for mot in self.ball_feeders:
            mot.motor.rotate_by_angle(angle=self.ball_feeder_cycle[self.current_ballfeeder_cycle_index], op_complete_callback=self._ball_feeder_next_step)
        
    def _ball_feeder_next_step(self, mot):
        if self.debug:
            print(f"Ball Feeder step {self.current_ballfeeder_cycle_index} complete. {self}")
        self.current_ballfeeder_cycle_index += 1
        if self.current_ballfeeder_cycle_index >= len(self.ball_feeder_cycle):
            # reached end of cycle --> waiting position
            if self.debug:
                print(f"Feeder cycle complete. {self._status=}")
            self.current_ballfeeder_cycle_index = -1
            # Moved to the async handling in run()
            # # set the machine status according to the current operation
            # self._status = self._status_requested
            # if self.debug:
            #     print(f"Machine status = {self._status}")
            return
        mot.rotate_by_angle(angle=self.ball_feeder_cycle[self.current_ballfeeder_cycle_index], op_complete_callback=self._ball_feeder_next_step)

    def set_ball_acceleration(self, bd_number: int, velocity: float, topspin: float, sidespin: float) -> None:
        motor_speeds = self.ballDrivers[bd_number].calc_motor_speeds(velocity, topspin, sidespin)
        self._set_ball_acceleration(bd_number, motor_speeds)

    def _set_ball_acceleration(self, bd_number: int, motor_speeds: List[int]) -> None:
        self.ballDrivers[bd_number].setMotorSpeeds(motor_speeds)

    def _play_shot(self, timer: Timer) -> None:
        """Play the next ball with the current settings and handle release cycle and shot cylcle"""
        self._release_next_ball()
        sleep(self.BALL_RELEASE_DURATION)
        # update the motors with possibly new settings
        if self._mode == MODE_PROGRAM:
            settings = self.ShotCycle.get_next_shot()
        elif self._mode == MODE_CONTINUOUS:
            settings = self.ContinuousShot
        if settings.MotorSettings is None:
            settings.init_for_bd(self.ballDrivers[settings.BallDriverNumber])
        self._set_ball_acceleration(settings.BallDriverNumber, settings.MotorSettings)
        # update ball frequency if changed
        if (self._currentBallFrequency != 1.0/settings.Pause) or not self.BallTimerRunning:
            if self.debug:
                print(f"Timer started or frequency changed from {self._currentBallFrequency} to {1.0/settings.Pause} bps")
            self._set_next_ball_frequency(1.0/settings.Pause)

    def _set_next_ball_frequency(self, new_frequency) -> None:
        """Changes the ball frequency without interrupting the running shot cycle
           However, it is designed for call between timer cycles, as it will interrupt a running timer.
        """        
        self._currentBallFrequency = new_frequency
        self.BallTimerRunning = False
        self.BallTimer.deinit()
        self.BallTimer.init(mode = Timer.PERIODIC, freq=new_frequency, callback=self._play_shot)
        self.BallTimerRunning = True
        
    def _start_playing_async(self) -> None:
        """starting to play balls following the current mode and state
           This method is to replace the old sync _start_playing() method and
           it can be used to start or resume the operation.
        """
        if self._status != STATUS_PLAYING:
            raise ImplementationException(f"RobbyController is not in the correct state ({self._status=}). Cannot start playing!")
        try:
            # give the ball driver motors time to spin up
            for bd in self.ballDrivers:
                bd.setMotorSpeeds(bd.calc_motor_speeds(.75, 0, 0))

            # start the stirrers
            self._start_stirrers()

            # get the next shot settings from the sequence and set the ball driver accordingly
            if self._mode == MODE_PROGRAM:
                shot_settings = self.ShotCycle.get_next_shot()
            elif self._mode == MODE_CONTINUOUS:
                shot_settings = self.ContinuousShot

            # start the ball motors
            self._set_ball_acceleration(shot_settings.BallDriverNumber, shot_settings.MotorSettings)

            # set the requested ball frequency
            self._currentBallFrequency = 1.0/shot_settings.Pause

            # use the timer callback function to play the ball and take care of the timer
            self._play_shot(self.BallTimer)
            # self.BallTimer.init(mode = Timer.PERIODIC, freq=self._currentBallFrequency, callback=self._play_shot)
            # self.BallTimerRunning = True
                
        except Exception as e:
            self._status = STATUS_ERROR
            raise e

    def _start_playing(self) -> None:
        """starting to play balls following the configured shot cycle"""
        if self._status != STATUS_IDLE and self._status != STATUS_ERROR:
            raise InvalidOperationException(f"RobbyController is still busy ({self._status=}). Cannot start playing!")
        try:
            self.mode = MODE_PROGRAM
            self._status = STATUS_PLAYING
            self.ShotCycle.reset()
            # get the next shot settings from the sequence and set the ball driver accordingly
            # do this first to give the motors some time to spin up
            shot_settings = self.ShotCycle.get_next_shot()
            self._set_ball_acceleration(shot_settings.BallDriverNumber, shot_settings.MotorSettings)
            # start the stirrers
            self._start_stirrers()
            # set the requested ball frequency
            release_immediately = True
            if release_immediately:
                self._currentBallFrequency = 0
                self._play_shot(self.BallTimer)
            else:
                self._currentBallFrequency = 1.0/shot_settings.Pause
                self.BallTimer.init(mode = Timer.PERIODIC, freq=self._currentBallFrequency, callback=self._play_shot)
                self.BallTimerRunning = True
        except Exception as e:
            self._status = STATUS_ERROR
            raise e
            

    def _stop_playing(self) -> None:
        self._status = STATUS_STOPPING
        err = None
        try:
            self._stop_feeders()
        except Exception as e:
            self._status = STATUS_ERROR
            err = e
        try:
            self._stop_balldrivers()
        except Exception as e:
            self._status = STATUS_ERROR
            err = e
        try:
            self._stop_stirrers()
        except Exception as e:
            self._status = STATUS_ERROR
            err = e
        try:
            self.BallTimer.deinit()
            self.BallTimerRunning = False
        except Exception as e:
            self._status = STATUS_ERROR
            err = e
        if err:
            self._status = STATUS_ERROR
            raise err
        else:
            self._status = STATUS_IDLE

    def _prepare_after_mount(self) -> None:
        """Move all parts into starting positions."""
        if self._status != STATUS_IDLE and self._status != STATUS_ERROR:
            raise Exception("RobbyController is still busy. Cannot perform preparation!")
        try:
            self._status = STATUS_PREPARING
            self._ball_feeder_prepare_after_mount()
        except Exception as e:
            self._status = STATUS_ERROR
            raise e
    
    @property
    def status(self) -> int:
        """Describes the current operation status of the machine (read-only)."""
        return self._status

    @property
    def mode(self) -> int:
        return self._mode
    @mode.setter
    def mode(self, value: int):
        """Gets or sets the current mode the machine is in. Only allowed if status==IDLE<br>
           0: continuous mode --> play the same shot until stopped<br>
           1: program mode --> play shot cycle<br>
           2: configuration --> calibrate and configure the machine<br>
        """
        if self._status != STATUS_IDLE:
            raise InvalidOperationException(f"Machine must be in status IDLE ({STATUS_IDLE}), but current mode is {self._mode}!")
        self._mode = value
    
    def request_mode_change(self, value: int):
        """Requests to change the machine mode.<br>
           This is the only way to control the operation mode in a thread-safe way. Calling the other methods directly, leads to execution on the cpu core of the caller!<br>
           0: continuous<br>
           1: program<br>
           2: configuration<br>
        """
        if self._mode != value:
            if self._status != STATUS_IDLE or self._status_requested != STATUS_IDLE:
                raise InvalidOperationException(f"Machine must be in status IDLE ({STATUS_IDLE}) before changing the operation mode, but current mode is {self._mode}!")
            self.lock_mode.acquire()
            self._mode_requested = value
            self.lock_mode.release()

    def issue_command_async(self, value: int):
        """Issues an async command to the machine, where only the values below are allowed.<br>
           This is the only way to control the operation (start/stop/pause) in a thread-safe way. Calling the other methods directly, leads to execution on the cpu core of the caller!<br>
           0: stop playing and reset to starting position<br>
           2: start or resume playing<br>
           3: pause playing, allowing to resume at the current position<br>
        """
        if value not in (STATUS_IDLE, STATUS_PLAYING, STATUS_PAUSED):
            raise InvalidOperationException(f"Invalid command issued ({value})!")
        if self._status != value:
            self.lock_status.acquire()
            self._status_requested = value
            self.lock_status.release()

    def getStatusData(self) -> dict:
        return {
            'mode': MODE_TEXTS[self._mode],
            'status': STATUS_TEXTS[self._status],
            'shot_cycle': self.ShotCycle.getStatusData(),
        }
    def getConfigData(self) -> dict:
        return {
            'settings': self.__general_settings.getConfigData(),
            'shot_cycle': self.ShotCycle.getConfigData(),
            'balldrivers': len(self.ballDrivers),
            'ballfeeders': len(self.ball_feeders),
            'ballstirrers': len(self.ball_stirrers),
            'machinerotators': len(self.machine_rotators)
        }

if __name__ == "__main__":
    # perform a test run for 30s
    print(f"Execution started")
    controller = RobbyController(debug=True)
    try:
        print(f"RobbyController initialized")
        controller._start_playing()
        print(f"Started playing")
        sleep(30)
        print(f"Slept for 30 sec")
        controller._stop_playing()
        while controller.status == STATUS_STOPPING:
            sleep(.1)
        print(f"Stopped playing")
    except KeyboardInterrupt:
        print(f"Interrupted")
        controller._stop_playing()
        print(f"Stopped playing after interrupt")
    except Exception as e:
        print(f"Exception caught: {e}")
        controller._stop_playing()
        print(f"Stopped playing after exception")
        raise e
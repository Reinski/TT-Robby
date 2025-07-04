# Copyright (c) 2024 Reiner Nikulski
# 
# This software is released under the MIT License.
# https://opensource.org/licenses/MIT
robby_version = "0.1.0"
import sys
if 'micropython' not in sys.version.lower():
    from typing import List, Union
from BallFeeder import BallFeeder
import BallFeeder as Bf
from BallStirrer import BallStirrer
from MachineRotator import MachineRotator
from Sg92r import Sg92r
from _thread import start_new_thread, allocate_lock
import gc
import json
from machine import Timer
from utime import sleep, sleep_ms
from BallDriver import BallDriver
from API import API
from RobbyExceptions import *
from RobbySettings import RobbySettings
import Shot
from ShotCycle import ShotCycle
from StepMotorPIO import StepMotorPIO, MODE_COUNTED, MODE_PERMANENT
import WebServer
from lib.RobbyLibrary import RobbyLibrary

# Machine mode
MODE_TEXTS = {0: 'direct', 1: 'program', 2: 'configuration'}
MODE_DIRECT = 0
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
KEY_LIBRARY = 'library'

class RobbyController:
    #TODO: Controller should have info/control about pin usage to prevent conflicts.
    #controller_pins = {} # key: GPIO pin number, value: dict with info on pins usage
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
           no_server: set to True to prevent webserver from starting, even if configured in the settings.
           debug: enable verbose output
        """
        #TODO: Failing to load some settings should not prevent loading the others.
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
            self.kill_requested = False
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

            
            txt_step = "Load Library"
            if self.debug:
                print("Initializing RobbyController: ", txt_step)
            self.Library = RobbyLibrary()
            if KEY_LIBRARY in settings:
                self.Library.load_from_config(settings[KEY_LIBRARY])
            else:
                if self.debug:
                    print("No library data found in settings, creating default one.")
                # create one default entry, using defaults
                self.Library.add_shot('example', Shot.get_default_shot_from_settings(self.__general_settings), "Example shot", "This is an example shot created because no shots were found in the settings.")

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
            self.ball_drivers: List[BallDriver] = []
            if KEY_BALL_DRIVERS in settings:
                for cfg in settings[KEY_BALL_DRIVERS]:
                    if cfg['motor_driver']['type'] == 'PCA9685':
                        try:
                            self.ball_drivers.append(BallDriver(bd_number=cfg['bd_number'], motor_angles=cfg['motor_angles'], i2c_channel=cfg['motor_driver']['i2c_channel'], sda_pin=cfg['motor_driver']['sda_pin'], address=cfg['motor_driver']['address'], debug=self.debug))
                            for motor in cfg['motors']:
                                self.ball_drivers[-1].motors[motor['motor_number']].polarity = motor['polarity']
                        except Exception as e:
                            self.errors.append(f"ERROR: Could not instantiate ball driver: {str(e)}")
                            print(self.errors[-1])
                    else:
                        raise NotImplementedError(f"Motor Driver class '{cfg['motor_driver']['type']}' has not been implemented yet!")
            else:
                if self.debug:
                    print("No ball drivers found in settings, creating default one.")
                self.ball_drivers.append(BallDriver(0, debug=self.debug))

            txt_step = "Ball Feeders Initialization"
            if self.debug:
                print(f"{len(self.ball_drivers)=}")
                print("Initializing RobbyController: ", txt_step)
            self.ball_feeders: List[BallFeeder] = []
            if KEY_BALL_FEEDERS in settings:
                for bf_cfg in settings[KEY_BALL_FEEDERS]:
                    feeder = Bf.create_from_config(bf_cfg=bf_cfg, bf_index=len(self.ball_feeders), debug=self.debug)
                    self.ball_feeders.append(feeder)
            else:
                if self.debug:
                    print("No ball feeders found in settings, creating default one.")
                # create one default entry, using defaults
                self.ball_feeders.append(BallFeeder(motor=StepMotorPIO(mode=MODE_COUNTED, debug=self.debug), bf_index=0, debug=self.debug))

            txt_step = "Ball Stirrers Initialization"
            if self.debug:
                print(f"{len(self.ball_feeders)=}")
                print("Initializing RobbyController: ", txt_step)
            self.ball_stirrers: List[BallStirrer] = []
            if KEY_BALL_STIRRERS in settings:
                for sub_cfg in settings[KEY_BALL_STIRRERS]:
                    if self.debug:
                        print(f"BallStirrer config: {sub_cfg}")
                    bs = BallStirrer(bs_index=len(self.ball_stirrers), motor=None, debug=self.debug)
                    bs.setConfigData(sub_cfg)
                    self.ball_stirrers.append(bs)
            else:
                if self.debug:
                    print("No ball stirrers found in settings, creating default one.")
                # create one default entry
                self.ball_stirrers.append(BallStirrer(bs_index=0, motor=StepMotorPIO(mode=MODE_PERMANENT, debug=self.debug), debug=self.debug))
            
            txt_step = "Machine Rotators Initialization"
            if self.debug:
                print(f"{len(self.ball_stirrers)=}")
                print("Initializing RobbyController: ", txt_step)
            self.machine_rotators: List[MachineRotator] = []
            if KEY_MACHINE_ROTATORS in settings:
                for cfg_rot in settings[KEY_MACHINE_ROTATORS]:
                    rotator = MachineRotator(mr_index=len(self.machine_rotators), debug=self.debug)
                    rotator.setConfigData(cfg_rot)
                    self.machine_rotators.append(rotator)
            else:
                if self.debug:
                    print("No machine rotators found in settings, creating default one.")
                # create one default entry
                self.machine_rotators.append(MachineRotator(0, debug=self.debug))

            txt_step = "BallTimer Initialization"
            if self.debug:
                print(f"{len(self.machine_rotators)=}")
                print("Initializing RobbyController: ", txt_step)
            self.BallTimer = Timer() # type: ignore
            self.BallTimerRunning = False
            self.current_program_index = -1
            """Current index in the shot cycle. Is -1 if in no program is started."""
            
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
        except Exception as e:
            print(f"Error during adopting settings, step {txt_step}: {e}")
            raise e

    def _is_any_ballfeeder_busy(self) -> bool:
        return len([bf for bf in self.ball_feeders if bf.is_busy()]) > 0
    
    def run_async(self):
        """Method to keep the controller in memory for async operation (endless loop until exception occurs).
           This method is to be used in a separate thread.
        """
        start_new_thread(self.run, ())

    def run(self):
        """Method to keep the controller in memory for async operation (endless loop until exception occurs)."""
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
                    if not self._is_any_ballfeeder_busy():
                        self._status = self._status_requested

                # State transition: * --> PAUSED
                if self._status_requested == STATUS_PAUSED:
                    if self.BallTimerRunning:
                        self.BallTimerRunning = False
                        self.BallTimer.deinit()
                    # the ball feeders will stop when reaching the waiting position, then we update the status:
                    if not self._is_any_ballfeeder_busy():
                        self._status = self._status_requested

                # State transition: * --> PLAYING
                if self._status_requested == STATUS_PLAYING:
                    if self._status != STATUS_PREPARING:
                        # Start the engines
                        self._status = STATUS_PREPARING
                        self._start_balldrivers()
                        self._start_stirrers()
                    # the ball feeders should be in the waiting position, then we can update the status:
                    if not self._is_any_ballfeeder_busy():
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

            if self.kill_requested:
                if self.debug:
                    print("Kill requested. Stopping controller.")
                self._status = STATUS_STOPPING
                self._stop_playing()
                #TODO: stop the webserver if running
                break
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
                KEY_BALL_DRIVERS: [bd.getConfigData() for bd in self.ball_drivers],
                KEY_BALL_FEEDERS: [bf.getConfigData() for bf in self.ball_feeders],
                KEY_BALL_STIRRERS: [bs.getConfigData() for bs in self.ball_stirrers],
                KEY_MACHINE_ROTATORS: [mr.getConfigData() for mr in self.machine_rotators]
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
        i = 0
        for bd in self.ball_drivers:
            try:
                bd.update_current_shot(self.__general_settings.default_ball_speed, self.__general_settings.default_topspin, self.__general_settings.default_sidespin)
                bd.start()
                i += 1
            except Exception as e:
                print(f"Error starting balldriver {bd.bd_number}: {e}")
        if self.debug:
            print(f"{i} balldrivers started.")

    def _stop_balldrivers(self) -> None:
        i = 0 # currently we have only one!
        for bd in self.ball_drivers:
            try:
                bd.stop()
                i += 1
            except Exception as e:
                print(f"Error stopping balldriver {i}: {e}")
        if self.debug:
            print(f"{i} balldrivers successfully stopped.")

    def _stop_feeders(self) -> None:
        i = 0
        for bf in self.ball_feeders:
            try:
                bf.stop()
                i += 1
            except Exception as e:
                print(f"Error stopping ball feeder {i}: {e}")
        if self.debug:
            print(f"{i} ball feeders successfully stopped.")

    def _ball_feeder_prepare_after_mount(self, bf_index: int) -> None:
        """Move the ball feeder into waiting position."""
        # Waiting position is after the last step of the ball feeder cycle. 
        if bf_index <0 or bf_index >= len(self.ball_feeders):
            raise InputDataException(f"Ball Feeder index out of range ({bf_index})!")
        if self.debug:
            print(f"Ball Feeder preparing after mount")
        bf = self.ball_feeders[bf_index]
        if bf.is_busy():
            raise InvalidOperationException(f"Ball Feeder #{bf_index} is currently operating and cannot be moved into the waiting position!")
        bf.prepare_after_mount()

    def _release_next_ball(self, bf_index: int) -> None:
        """Trigger the feeder cycle for the next ball"""
        bf = self.ball_feeders[bf_index]
        if bf.is_busy():
            raise ImplementationException("Ball Feeder not finished with previous operation.")
        if self.debug:
            print(f"Ball Feeder releasing next ball")
        bf.dispense()
        
    def _play_shot(self, timer: Timer) -> None:
        """Play the next ball with the current settings and handle release cycle and shot cylcle"""
        if self._mode == MODE_PROGRAM:
            shot_settings = self.ShotCycle.get_current_shot()
        elif self._mode == MODE_DIRECT:
            shot_settings = self.ContinuousShot
        else:
            raise InvalidOperationException(f"Cannot play shot in mode {self._mode}. Only PROGRAM and DIRECT modes are supported.")

        #TODO: We need the BallFeederNumber here, but it would make more sense to maintain Driver-Feeder relations somewhere.
        #Until that's implemented, we use the driver number also as feeder number.
        self._release_next_ball(shot_settings.BallDriverNumber) # the releasing still belongs to the current shot
        sleep(self.BALL_RELEASE_DURATION)
        # update the motors with possibly new settings
        if self._mode == MODE_PROGRAM:
            settings = self.ShotCycle.get_next_shot()
        elif self._mode == MODE_DIRECT:
            settings = self.ContinuousShot
        self.ball_drivers[settings.BallDriverNumber].update_from_shot(settings)
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
        if self._status != STATUS_IDLE and self._status != STATUS_ERROR:
            raise ImplementationException(f"RobbyController is not in the correct state ({self._status=}). Cannot start playing!")
        try:
            # get the next shot settings from the sequence and set the ball driver accordingly
            if self._mode == MODE_PROGRAM:
                if self._status == STATUS_IDLE:
                    self.ShotCycle.reset()
                shot_settings = self.ShotCycle.get_next_shot()
            elif self._mode == MODE_DIRECT:
                shot_settings = self.ContinuousShot
            self._status = STATUS_PLAYING

            # start the ball motors (as early as possible)
            self.ball_drivers[shot_settings.BallDriverNumber].update_from_shot(shot_settings)

            # start the stirrers
            self._start_stirrers()

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
        """starting to play balls in the direct or the program mode, following either the ContinuousShot or the configured shot cycle"""
        if self._status != STATUS_IDLE and self._status != STATUS_ERROR:
            raise InvalidOperationException(f"RobbyController is still busy ({self.status_text=}). Cannot start playing!")
        if self._mode != MODE_PROGRAM and self._mode != MODE_DIRECT:
            raise InvalidOperationException(f"RobbyController must be in program or direct mode ({self.mode_text=}). Cannot start playing!")
        try:
            # get the next shot settings from the sequence and set the ball driver accordingly
            # do this first to give the motors some time to spin up
            if self._mode == MODE_PROGRAM:
                if self._status == STATUS_IDLE:
                    self.ShotCycle.reset()
                shot_settings = self.ShotCycle.get_next_shot()
            elif self._mode == MODE_DIRECT:
                shot_settings = self.ContinuousShot
            self._status = STATUS_PLAYING
            # give the ball driver motors time to spin up for the first shot
            self.ball_drivers[shot_settings.BallDriverNumber].update_from_shot(shot_settings)
            # start the stirrers
            self._start_stirrers()
            # set the requested ball frequency
            release_immediately = False
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
        errors = []
        try:
            self.BallTimer.deinit()
            self.BallTimerRunning = False
        except Exception as e:
            self._status = STATUS_ERROR
            errors.append(e)
        try:
            self._stop_feeders()
        except Exception as e:
            self._status = STATUS_ERROR
            errors.append(e)
        try:
            self._stop_stirrers()
        except Exception as e:
            self._status = STATUS_ERROR
            errors.append(e)
        try:
            self._stop_balldrivers()
        except Exception as e:
            self._status = STATUS_ERROR
            errors.append(e)
        if errors:
            self._status = STATUS_ERROR
            raise InvalidOperationException(f"Errors occurred while stopping the machine: {', '.join(str(e) for e in errors)}")
        else:
            self._status = STATUS_IDLE

    def _prepare_after_mount(self) -> None:
        """Move all parts into starting positions after the machine has been assempled.
           It is questionable if this still makes sense on the machine level, as you would either:
           - assemble the machine from scratch and then prepare the single parts individually or
           - assemble only single parts and then again prepare them individually or
           - just place the machine without need to assemble it and the no need to prepare anything after mount.
        """
        if self._status != STATUS_IDLE and self._status != STATUS_ERROR:
            raise Exception("RobbyController is still busy. Cannot perform preparation!")
        try:
            self._status = STATUS_PREPARING
            for bf in self.ball_feeders:
                bf.prepare_after_mount()
        except Exception as e:
            self._status = STATUS_ERROR
            raise e
    
    @property
    def status_text(self) -> str:
        """Describes the current operation status of the machine (read-only)."""
        return STATUS_TEXTS[self._status]
    @property
    def status(self) -> int:
        """Returns the current operation status of the machine (read-only)."""
        return self._status

    @property
    def mode_text(self) -> str:
        return MODE_TEXTS[self._mode]

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
            raise InvalidOperationException(f"Machine must be in status IDLE ({STATUS_IDLE}), but current status is {STATUS_TEXTS[self._status]} ({self._status})!")
        self._mode = value
        if self._mode == MODE_DIRECT:
            self.ball_drivers[self.ContinuousShot.BallDriverNumber].update_from_shot(self.ContinuousShot)
        if self.debug:
            print(f"Mode changed to {self.mode_text} ({self._mode})")
    
    def set_continuous_shot(self, bd_number: Union[int, None]=None, v_ball_norm: Union[float, None]=None, w_h_norm: Union[float, None]=None, w_v_norm: Union[float, None]=None, pause_seconds: Union[float, None]=None) -> None:
        """Sets the continuous shot settings, which will be used in continuous mode.
           Only specified values will be changed, the others remain as they are.
           The values are normalized to 1.0, so 1.0 means maximum speed.
        """
        if self._mode != MODE_DIRECT:
            raise InvalidOperationException(f"Machine must be in direct mode ({MODE_DIRECT}), but current mode is {self._mode} ({self.mode_text})!")
        if v_ball_norm:
            self.ContinuousShot.BallSpeed = v_ball_norm
        if w_h_norm:
            self.ContinuousShot.Topspin = w_h_norm
        if w_v_norm:
            self.ContinuousShot.Sidespin = w_v_norm
        if pause_seconds:
            self.ContinuousShot.Pause = pause_seconds
        if bd_number:
            self.ContinuousShot.BallDriverNumber = bd_number

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
        if self.mode not in (MODE_PROGRAM, MODE_DIRECT):
            raise InvalidOperationException(f"Machine must be in program ({MODE_PROGRAM}) or direct ({MODE_DIRECT}) mode to issue commands, but current mode is {self.mode} ({self.mode_text})!")
        if self._status != value:
            self.lock_status.acquire()
            self._status_requested = value
            self.lock_status.release()

    def getStatusData(self) -> dict:
        return {
            'mode': self.mode,
            'mode_text': self.mode_text,
            'status': self._status,
            'status_text': STATUS_TEXTS[self._status],
            'shot_cycle': self.ShotCycle.getStatusData(),
            'continuous_shot': self.ContinuousShot.getConfigData(),
        }
    def getConfigData(self) -> dict:
        return {
            'settings': self.__general_settings.getConfigData(),
            'shot_cycle': self.ShotCycle.getConfigData(),
            'balldrivers': len(self.ball_drivers),
            'ballfeeders': len(self.ball_feeders),
            'ballstirrers': len(self.ball_stirrers),
            'machinerotators': len(self.machine_rotators)
        }

    def update_continuous_shot(self, bd_number: int, v_ball_norm: Union[float, None]=None, w_h_norm: Union[float, None]=None, w_v_norm: Union[float, None]=None, pause_seconds: Union[float, None]=None) -> None:
        """Updates the continuous shot settings in the controller."""
        if self._mode != MODE_DIRECT:
            raise InvalidOperationException(f"Machine must be in direct mode ({MODE_DIRECT}), but current mode is {self._mode} ({self.mode_text})!")
        
        if bd_number < 0 or bd_number >= len(self.ball_drivers):
            raise InputDataException(f"Ball Driver index out of range ({bd_number})!")
        if v_ball_norm is not None:
            self.ContinuousShot.BallSpeed = float(v_ball_norm)
        if w_h_norm is not None:
            self.ContinuousShot.Topspin = float(w_h_norm)
        if w_v_norm is not None:
            self.ContinuousShot.Sidespin = float(w_v_norm)
        if bd_number != self.ContinuousShot.BallDriverNumber:
            if self.debug:
                print(f"Changing ball driver for continuous shot from {self.ContinuousShot.BallDriverNumber} to {bd_number}")
            self.ball_drivers[self.ContinuousShot.BallDriverNumber].stop() # stop the old ball driver
            self.ContinuousShot.BallDriverNumber = bd_number # update the motor settings for the new ball driver
        self.ball_drivers[bd_number].update_from_shot(self.ContinuousShot)
        if pause_seconds is not None:
            self.ContinuousShot.Pause = pause_seconds

if __name__ == "__main__":
    # perform a test run for 30s
    print(f"Execution started")
    controller = RobbyController(debug=True, no_server=True)
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
# Robby Machine Controller
## General Overview
The Machine Controller is the micropython software that controls the operation of the ball machine. It provides an http REST-API to be called by any clients.  
Currently, the machine controller is designed to run a single Raspberry Pi Pico W and even only on a single core, due to problems with multiprocessing under micropython.
## Installation
The machine controller must be transferred onto the Pico board by flashing the micropython firmware.  
... description to be done ...
## Calibration
Due to the lack of sensors which could report the actual positions of movable parts, the software must keep track about this itself. Therefore it must have a known starting point (defined position of all movable parts) into which all parts must be brought manually before using the machine. This is the purpose of the machine calibration routine.  
... description to be done ...
## Controller Description
### Mode of Operation
The most basic setting of the machine is its mode of operation:
- calibration mode
  Before the machine can start operating, all movable parts must be brought to a defined position.
- continuous mode
  When started, the machine is playing the same shots in a constant interval until it is stopped.
- program mode
  When started, the machine is playing shots following the selected program until it is stopped. A program defines a sequence of shots that can differ in speed, spin and timing. 
### Calibration
### Continuous Mode
This is the most basic mode, as it keeps playing the same balls over and over again, until it is stopped.  
Parameters are:
- ball speed
- ball spin
- pause time before next shot
### Program Mode
The machine can execute predefined shot cycles, so-called programs. A program consist of multiple shots, where each shot has these parameters:
- ball speed
- ball spin
- pause time before next shot
- number of repetitions (default: 1)
- pause time between repetitions (default: pause time before next shot)
Planned extensions:  
When the machine supports automatic tilt and swivel, then these parameters can be added:
- swivel angle
- tilt angle

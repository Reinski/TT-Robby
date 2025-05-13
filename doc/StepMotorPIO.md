# Controlling Stepper Motor via Raspberry Pi Pico PIO and MicroPython
## Concept
PIO state machines are used to asynchronously operate the stepper motor, so that the main program is not blocked.
### Main Program Controller
This is a micropython program for these top-level tasks:
- Holds constant data definitions, like pin numbers, step sequences etc.
- Controls dynamic operation parameters, like number of steps, motor speed
- Starts and stops motor operation
- Converts data into appropriate units/formats where required
### PIO – SM1
This is the top-level state machine and its tasks are:
- Trigger each motor step
- Keep track of the number of steps left to go
- Inform the main program when it is finished

Input parameters (pulled from TX-queue):
- Number of steps
### PIO – SM2
This state machine is mainly for controlling the speed and has these tasks:
- Wait for trigger from SM1
- Trigger single motor step
- Take care about the time delay to next motor step

In case speed is constant, this SM can be omitted and SM1 can trigger SM3 directly
### PIO – SM3
This state machine has these tasks:
- Wait for trigger from SM2 (or from SM1 if speed is constant)
- Take care about the pin settings for the next step
- Control the output pins

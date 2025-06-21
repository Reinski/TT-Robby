# Code snippets
## REPL
These snippets can be executed directly in the REPL.
### Create controller object
Import the library and create an instance of RobbyController.
```python
from lib.RobbyController import RobbyController
controller = RobbyController(debug=True, no_server=True)
print(f"Current state: {controller.mode_text} ({controller.mode}), {controller.status_text} ({controller.status})")
```
This does three things:
1) enable debug messages
2) prevent the REST-API webserver from being started
3) print the current state of the machine
Unfortunately, the controller becomes unresponsive or gets other problems if the webserver is started.
### Configuration mode
The following lines enable the configuration mode and prints the current config and status of the machine. Finally it prints the full config of the first ballbriver.
```python
controller.mode = 2
print(f"Current state: {controller.mode_text} ({controller.mode}), {controller.status_text} ({controller.status})")
print(controller.getConfigData())
print(controller.getStatusData())
print(controller.ball_drivers[0].getConfigData())
```
Note that the getConfigData methods are returning dictionaries, which is useful when building APIs for external clients and which is actually used for the existing REST-API. The same dictionary structure can be used to modify the configuration as a whole (Now we use a ball_feeder, as this is not yet implemented for ball_drivers):
```python
config = controller.ball_feeders[0].getConfigData() # receive the current config
config['bf_index'] = 1                              # change something in the config
controller.ball_feeders[0].setConfigData(config)    # pass the whole changed config back
print(controller.ball_feeders[0].getConfigData())   # see that the changes were adopted
```
Note that this example doesn't necessarily make any sense. ;-)  
#### Test ball driver
You can use the config mode for testing your setup. E.g. test the ball driver motors by executing this line by line and see what happens:
```python
controller.mode = 2                                             # activate config mode
controller.ball_drivers[0].update_current_shot(v_ball_norm=.75) # change the ball speed for current shot to 75%
controller.ball_drivers[0].start()                              # start the ball driver with this setting
controller.ball_drivers[0].update_current_shot(v_ball_norm=.5)  # reduce the ball speed to 50%
controller.ball_drivers[0].stop()                               # stop all ball driver motors
```
You can also test the individual motors:
```python
controller.ball_drivers[0].motors[1].start()       # start the 2nd motor of first ball driver
controller.ball_drivers[0].motors[1].set_speed(75) # set its speed to 75%
controller.ball_drivers[0].motors[1].stop()        # stop the motor again
```
#### Test ball feeder
```python
controller.mode = 2                                  # activate config mode
controller.ball_feeders[0].dispense()                # execute the cycle for dispensing one ball
print(controller.ball_feeders[0].getConfigData())    # get the ball feeder's configuration
print(controller.ball_feeders[0].motor_states[0][1]) # print the action cycle (last index 1) of the frist motor (index 0) of the first feeder (index 0)
controller.ball_feeders[0].stop()                    # stop all ball feeder motors (in case they are still running)
```

### Direct Control mode
```python
controller.mode = 0
print(f"Current state: {controller.mode_text} ({controller.mode}), {controller.status_text} ({controller.status})")
``` 
This enables the direct mode, which repeats the same shot in a fixed interval. However, it allows direct adjustment of the shot's properties, even during playing.
```python
cs_cfg = controller.ContinuousShot.getConfigData() # get the current shot config
print(cs_cfg)                                      # display it
# now let's increase the time between shots by 1 second
controller.update_continuous_shot(bd_number=cs_cfg['bd_number'], pause_seconds=cs_cfg['pause']+1.0)
print(cs_cfg)                                      # display the updated shot
```
Basically, the code should look something like this - but unfortunately the controller becomes unresponsive after some seconds (a bug probably related to the StepMotors and PIO):
```python
controller._start_playing()                              # start playing with the current shot settings
controller.update_continuous_shot(0, 1.0, 0.0, 0.0, 2.0) # modify the current shot settings
controller._stop_playing()                               # stop playing
```
### Program mode
```python
controller.mode = 1
print(f"Current state: {controller.mode_text} ({controller.mode}), {controller.status_text} ({controller.status})")
```
This enables the program mode, which plays predefined sequences of shots.  

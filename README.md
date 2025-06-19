# TT-Robby
## Overview
TT-Robby is a hobby project to design a tabletennis ball machine with focus on affordability by hobby players.
The concept is based on using 3D printed parts whereever possible and otherwise cheap components. The tradeoff is a higher requirement of time in comparison to buyable out-of-the-box solutions, invested into printing, assembling and adjusting the whole machine.  
Another goal is high flexibility through modularity in both, construction and programming.
## Getting started
Unfortunately, there is no fool-proof concept that will work out of the box. So this project is still in a tinkering state (PoC). If you want to get a feeling for the basic concept without investing too much time and effort, then I'd suggest the following:
- Print 6x ball_lead-pole_100mm and 3 ball_lead-orthogonal_ring, assemble a straight tube, take a tt-ball and play around with it.
- If you like what you see, print 2 more rings and 3 more poles and add an orthogonal branch in your previous construction (hint: replace one pole with a ring).
- If you still want to continue, then you need to invest some money, as you should start with the electronics now. I find it most satisfying to see the machine fire some balls, so I'd suggest starting with building the Ball Driver:  
  From the BoM below, buy at least 2 DC motors, a raspi pico and the Motor Driver Module plus you'll want some dev equipment like a breadboard, wires, usb-cable etc. plus you'll need some IDE to operate the motors.
- Now, if you're still motivated to go for it, you can have a look at the rest and help finding solutions for all the open issues.
## Bill of material
### Simplest Setup
No side-spin, fix ball direction
- Raspberry Pi Pico W or WH (~8€)
- 2 x DC Toy Hobby Motor - 130 Size 4.5V to 9V (~2€ each)
- 1 x WaveShare DC Motor Driver Module (https://www.waveshare.com/wiki/Pico-Motor-Driver) (~30€)
- 1 x 28BYJ-48 stepper motor 5V DC + ULN2003 driver board (~2.20€ each)
- 2 Rubber rings (50x4mm; Diameter approx. 30mm) 
- Wires + boards
- 3D printing filament
- some tools for printing post-processing and for (dis)assembling (e.g. pliers)
### Max setup
All currently supported features: Top spin, back spin, side-spin, fix ball direction
- Raspberry Pi Pico W or WH (~8€) (Pico2 not tested yet)
- 3 x DC Toy Hobby Motor - 130 Size 4.5V to 9V (~2€ each)
- 1 x WaveShare DC Motor Driver Module (https://www.waveshare.com/wiki/Pico-Motor-Driver) (~30€)
- 2 x 28BYJ-48 stepper motor 5V DC + ULN2003 driver board (~2.20€ each)
- 2 x Sg92r servo motors
- 3 Rubber bands (50x4mm; Diameter approx. 30mm)
- Wires + boards
- 3D printing filament
- some tools for printing post-processing and for (dis)assembling (e.g. pliers)
## Open points
To give a rough overview about the maturity of this project, here are some open issues. Details can be found at the specific components' sections below.
- Ball Feeder with current pushing geometry and stepper motor is not fast enough to serve 1 ball/sec. New conncept is in test, though.
- Concept for Ball Pool must be finalized
- Concept for Ball Recirculation is open
- Concept for Direction Control (automated rotation and tilt) has to be completed. Esp. tilt is missing.
- Power Supply specification for the Ball Driver motors must still be defined.
- Suitability of the 130 size DC toy motors is questionable (although latest tests indicate that two of them are ok for basic funcitonality)
- Wiring and casing geometry is still to be designed
- Control concept and its implementation is incomplete (Controller API)
## Components
This section describes the ball machine's components in detail. The components are listed in alphabetic order.
### Ball Driver
Probably being the most important part of the machine, the Ball Driver is responsible to accelerate the ball with the required attributes of 
- transversal speed
- transversal direction
- spin speed
- spin axis  
  The concept is to have three wheels accelerating the ball from different angles with individual values, so that the forward speed and the rotation speed and axis is determined by the different wheel speeds.
  The forward direction is controlled by the ball lead (always co-axial), so that it can only be controlled by pivoting (left/right) and tilting (up/down) the whole Ball Driver to point into the required direction.
  If a mechanic is implemented to change orientation its minimum requirements shall be:
- pivot angle >= 45°
- tilt angle at least from -45° to +15° (-45° is intended for simulating specific serves, but is certainly not the highest priority)
  In case of downwards tilt a premature release of the ball should be prevented (i.e. gravity should not drag the balls into the driver)
#### Open points
- Power Supply
  Power output from Raspi Pico is too weak for operating the three motors. So a concept is required to provide power to the motors with adequate electrical properties.
  The aim should be:
  - have only one power plug into standard socket (AC)
  - have enough power to operate all motors at full speed
  - have stable power supply for the controller board
  - have the power related elements stored away in some containment to avoid user contact and reduce negative environmental influence (dust, moisture)
  - keep the whole electrical system at an adequate temperature
- Motor Suitability
  The currently used 130 sized DC toy motors are very cheap and have a nice speed, but are very weak and not very responsive to control commands (high inertia-to-power ratio).
  Although they proved capable of driving a ball plain forward at sufficient speed (no spin) - even with just two motors, they must still be testet if they are really suitable under field conditions.
- Orientation Control
  A horizontal swivel has now been designed and seems ok. However, it turns the whole main part of the machine and the decoupling from both, the stand and the Ball Pool, is currently not very satisfying. 
  For the vertical control there is currently no concept implemented.
  A concept should include motor specification, component geometry, ball leading concept for the varying angles.
  Until such a concept is designed, TT-Robby has a fixed ball direction and must be manually oriented into the wanted direction.
- Wiring and Casing
  Wires must be lead in a way that they cannot interfere with the component's operation (turning wheels, moving parts), but still can be easibly mounted and unmounted. This also includes a concept for connectors making the installation more comfortable to the user.  
  Electronic components like the microcontroller on the motor driver shield and also the motors themselves should be located in safe places to provide safety for them and for the operators. An according design is required.
### Ball Feeder
The Ball Feeder has the task to feed the next ball in a controlled manner into the Ball Driver, i.e. directly into the place where the ball is caught by the Ball Driver's wheels. This should happen independently of the Ball Driver's (including the feeder) current orientation, esp. regardless of the relative direction of gravity.
While the Ball Pusher (a turnstile-like design, see below) is able to push a single ball further while holding back the next one, its current geometry prevents it from being able to push the ball far enough into the feeding position.
As an alternative, a piston concept has been designed, which is able to push the ball far enough into the ball driver. However, the current concept takes too long for one sequence, so it needs refactoring.
### Ball Leads
On the whole way from the Ball Pool to the Ball Driver, each ball must always be in a controlled location to avoid disturbances in the operation.
While many machines use tubes or otherwise fully encased constructions to guide the balls in a controlled manner, TT-Robby uses a modular system of combining various segments, basically consiting of 3 co-axial leading poles carried by rings.
The poles are connected to the rings by sticking them through accordingly shaped openings in the rings. Using this principle, more elements can be attached in the same manner either to the rings or to the poles.
### Ball Pool
The Ball Pool is the main reservoir to hold the ball supply for the machine. In normal operation mode it is the only way to feed balls from outside into the machine.  
Designed basically as a big funnel, open at the top and with a ball-sized opening at the bottom, it follows a very simplistic approach.
In the concept phase, a funnel made out of cardboard had been used, which basically fulfilled its task. Meanwhile, a 3d printed ball pool was designed, as integrating the pool in a controlled manner into the machines geometry was problematic with the cardboard-approach.  
However it must be said, that the handling of the 3d-printed ball pool is quite uncomfortable, as it follows the modular concept and as a consequence is not very stable.
#### Open points
- Improve design of the pool itself: It has weak stability when applying force e.g. during assembly.
- Improve ball outlet geometry: Find a statically determined geometry, where all parts go into their pre-defined places.
- Find a concept for reliably supplying balls into the moving part of the machine (i.e. the Ball Driver).
### Ball Pusher
To transport the balls through the whole system (see Ball Leads), finally arriving sequentially at the Ball Driver, they need to be moved independently of their natural tendencies caused by gravity, bouncing etc.  
The Ball Pusher is a cross-shaped wheel (turnstile-like) driven by a step motor, which pushes one ball at a time and lets the next ball move into place. Multiple Ball Pusher components can be attached to Ball Leads whereever required.  
Currently the concept is not used, as instead a more simplistic approach is applied, where the balls are dropping out of the Ball Pool into the Ball Leads and move through them, pulled by gravity.
### Ball Recirculation
After balls have been hit by the player, it would be most convenient to automatically bring them back into the machine, hence creating a full cycle. Most ball machines make use of nets catching the played balls directly near the edges of the table and leading them - dragged by gravity - back into the Ball Pool.  
Despite this being a quite effective concept, it has the downside, that the nets plus their holders are a cost factor and mean quite high effort to assemble before each training session.
Since I am a lazy person, I'm still thinking of an alternative approach.
Until that is found, TT-Robby omits the Ball Recirculation Concept and instead relies on the manual work to collect the served balls and fill them back into the Ball Pool.
### Direction Control / Rotator
The balls' forward direction should be machine-controllable, i.e. the pivot and the tilt of the ball driver must be changeable.  
In the basic setup, this is a manual process by the user simply changing the machine's orientation (see also Machine Mount).
First approach for changing the horizontal direction has been implemented and the name "Rotator" has been established. Since also the tilt is probably controlled by rotation, this name can be used generally.
#### Open Points
- Define overall concept: Orientate the whole machine incl. Ball Pool or orientate just the Ball Driver+Feeder?
- Design mechanical geometry for the selected concept.
- In case of only parts of the whole system change their orientation: Solve problems for a smooth ball transition between static and movable ball leads.
- Define motors to use
- Implement controller logic
### Machine Controller
The Machine Controller is the software running on the Pi Pico and has the task to control the machine parts (motor speeds and orientations). For this it translates the user's requirements (mainly direction, speed, spin and interval) into the technical commands to the motors. It may also be responsible for providing access to the current settings or reflecting them back to the user.
Currently, the plan is to have a REST-API for the user commands which could then be accessed from Apps on a mobile device or even a JavaScript UI running in the local browser.
In its current state the controller program already supports the translation of most user commands into machine control commands and even allows to define ball sequences (changing spin, speed, interval between single balls).
#### Open Points
- REST API
- Security concept (API tokens?)
- Stability tests
- Demonstration UI
### Machine Mount
Where shall TT-Robby be mounted? Currently it must be placed directly on the table surface, but even then it needs some sort of a stand to be designed.  
Idea is to design a simple table surface stand in the first step being easily replacable by other solutions which may be created later.
To achieve this flexibility, a connector concept between the ball machine and the stand shall be implemented.
Options for the stand are:
- Place directly on table
- Attach to table by clamp or something similar
- Place on an own stand (maybe attach to standard camera tripod)
- Direction Control could be implemented in the stand and not into the ball machine itself
#### Open Points
- Design mount connectors
- Design simple stand
- Design flexible mount, allowing rotation and tilt - if this is not a feature of the ball driver alone.
## Specifications
These are the minimum specifications that should be met by the fully configured machine.
- As cheap as possible
- Shot frequency: 1 balls/sec
- Ball forward speed: 100 km/h
- Ball rotation: up to 100 rpm
- Shot direction angle, horizontal rotation: 90°
- Shot direction angle, up/down: 45°
- Fully Controllable via App
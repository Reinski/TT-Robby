<!--
 Copyright (c) 2023 Reiner Nikulski
 
 This software is released under the MIT License.
 https://opensource.org/licenses/MIT
-->
# DebugProbe
Unfortunately, via the pico-w-go extension it is not possible to interactively debug code (i.e. set breakpoints, step through etc.) running on a directly connected pico.
One solution is using another Raspberry Pi Pico as a debug probe, which means it works as a USB to SWD/UART bridge.
The debug probe is then connected to your PC and the target pico is connected to the probe.
This approach to achieve interactive debugging functionality in VSCode is described here.
It is based on the official getting-started documentation: https://datasheets.raspberrypi.com/pico/getting-started-with-pico.pdf.
More unfortunately: All effort failed! There doesn't seem to be a way to interactively debug micropython programs running on a pico 

## Software requirements
- VSCode
- openOCD
- debugprobe.uf2 or picoprobe.uf2
## Hardware requirements
- Windows PC as development platform (tested on Windows 10 Pro)
- Raspberry Pi Pico as debug probe (tested with basic pico w/o WLAN)
- Raspberry Pi Pico as the target pico, which needs to be debugged
- Breadboard(s) for wiring it all together
## Skill requirements
- Browsing the internet & Downloading software
- Sticking pins or wires into the right holes on a breadboard
- Soldering (can possibly get around it if the Picos do already have headers --> H-variants)
- For this documentation: Some basic skill to handle files and folders in Windows and at the command prompt (cmd.exe)

## Installation
### Install VS Code and extensions
The installation of VSCode is not covered here. Extensions I used in the given context:
- Python by MS
- Pylance by MS
- Pico-W-Code by paulober
All extensions could be installed as described in their documentation.
### Flash debug probe
- From [github repository](https://github.com/raspberrypi/picoprobe/releases) download
  - debugprobe.uf2 (or picoprobe.uf2)
- Connect the debug probe via USB cable to your running Windows PC:
  - Hold down the BOOTSEL button
  - Connect probe via USB to PC
  - Wait until explorer opens the pico as new usb drive
    If that doesn't happen, you might have a poor usb cable (no data wires), so try another one.
  - Release the BOOTSEL button
  - Copy the .uf2 file to the usb drive (root folder)
    The drive will immediately dissappear, as the pico starts flashing its firmware.
    In my case, Windows informed me after some seconds, that a new device was ready for use, which I took as confirmation that flashing was successful.
    Also, the LED on the pico will be turned on.
  
### Flash target pico
- Download the uf2 file for micropython from (...)
- Hold down the BOOTSEL button
- Connect probe via USB to PC
- Wait until explorer opens the pico as new usb drive
  If that doesn't happen, you might have a poor usb cable (no data wires), so try another one.
- Release the BOOTSEL button
- Copy the .uf2 file to the usb drive (root folder)
  The drive will immediately dissappear, as the pico starts flashing its firmware.
  In my case, Windows informed me after some seconds, that a new device was ready for use, which I took as confirmation that flashing was successful.

### Install openOCD
- Search and download precompiled binaries/package for Windows
- Simply copy the main folder into the programs folder of your Windows
- Test installation:
  - Open cmd.exe
  - Go into the installation folder "OpenOCD-..."
  - run openOCD:  
    ```bin\openocd.exe```  
    If you see something like this, then it was a success:
    ```Open On-Chip Debugger 0.12.0 (2023-06-21) [https://github.com/sysprogs/openocd]
    Licensed under GNU GPL v2
    libusb1 09e75e98b4d9ea7909e8837b7a3f00dda4589dc3
    For bug reports, read
            http://openocd.org/doc/doxygen/bugs.html
    embedded:startup.tcl:28: Error: Can't find openocd.cfg
    in procedure 'script'
    at file "embedded:startup.tcl", line 28
    Info : Listening on port 6666 for tcl connections
    Info : Listening on port 4444 for telnet connections
    Error: Debug Adapter has to be specified, see "adapter driver" command
    embedded:startup.tcl:28: Error:
    in procedure 'script'
    at file "embedded:startup.tcl", line 28
    ```
### Wire your devices
Connect debug probe with target pico and finally plug the usb cable from the debug probe into the PC.
Wiring can be found in the official getting-started documentation in Appendix A (link see on top), 
### Check connection
According to the docs, this line should somehow signal you success (I guess, the referenced cfg files need not exist(?)):  
```bin\openocd -f interface/cmsis-dap.cfg -c "adapter speed 5000" -f target/rp2040.cfg -s tcl```  
However, I only receive this:
```Open On-Chip Debugger 0.12.0 (2023-06-21) [https://github.com/sysprogs/openocd]
Licensed under GNU GPL v2
libusb1 09e75e98b4d9ea7909e8837b7a3f00dda4589dc3
For bug reports, read
        http://openocd.org/doc/doxygen/bugs.html
adapter speed: 5000 kHz
Info : Hardware thread awareness created
Info : Hardware thread awareness created
Info : Listening on port 6666 for tcl connections
Info : Listening on port 4444 for telnet connections
Info : Using CMSIS-DAPv2 interface with VID:PID=0x2e8a:0x000c, serial=E6616408437D1831
Info : CMSIS-DAP: SWD supported
Info : CMSIS-DAP: Atomic commands supported
Info : CMSIS-DAP: Test domain timer supported
Info : CMSIS-DAP: FW Version = 2.0.0
Info : CMSIS-DAP: Interface Initialised (SWD)
Info : SWCLK/TCK = 0 SWDIO/TMS = 0 TDI = 0 TDO = 0 nTRST = 0 nRESET = 0
Info : CMSIS-DAP: Interface ready
Info : clock speed 5000 kHz
Error: Failed to connect multidrop rp2040.dap0
```
According to internet sources, this means, debug probe was found, but the connection to the taget pico is not working.
Options:
- Check all cables - OK
- Try other target pico - non available
- Try with picoprobe.uf2 instead debugprobe.uf2
- openocd language dependent? -> micropython
- usb driver??
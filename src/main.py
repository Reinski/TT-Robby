# TT-Robby
# Copyright (c) 2025 Reiner Nikulski
# 
# This software is released under the MIT License.
# https://opensource.org/licenses/MIT
from lib.RobbyController import RobbyController, STATUS_PREPARING
from lib.WebServer import WebServer
from machine import Pin

if __name__ == "__main__":
    print(f"Signal 'execution started' by switching LED on.")
    pin = Pin("LED", Pin.OUT)
    pin.on()
    print("Initializing.")
    # start web server
    try:
        webserver = WebServer(debug=True)
        controller = RobbyController(no_server=True, debug=True)
        webserver.run(controller)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        raise e
    finally:
        pin.off()

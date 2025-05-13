# TT-Robby
# Copyright (c) 2023 Reiner Nikulski
# 
# This software is released under the MIT License.
# https://opensource.org/licenses/MIT
from lib.RobbyController import RobbyController
from lib.WebServer import WebServer
from utime import sleep

def perform_test():
    # perform a test run for 60s
    print(f"Execution started")
    controller = RobbyController()
    try:
        print(f"RobbyController initialized")
        controller._start_playing()
        print(f"Started playing")
        sleep(60)
        print(f"Slept for 30 sec")
        controller._stop_playing()
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

if __name__ == "__main__":
    webserver = WebServer(debug=True)
    controller = RobbyController(no_server=True, debug=True)
    webserver.run(controller)
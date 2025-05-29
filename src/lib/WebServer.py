# Copyright (c) 2023 Reiner Nikulski
# 
# This software is released under the MIT License.
# https://opensource.org/licenses/MIT
import sys
if 'micropython' not in sys.version.lower():
    from typing import List, Union
import gc
import json
import network
import re
import socket
import time
import RobbyController
from RobbyExceptions import InputDataException, ImplementationException

# WiFi
# HTML
def getHtmlResponse_data(data: dict):
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><link rel="shortcut icon" href="data:"><title>TT-Robby</title></head><body>{data}</body></html>"""
def getHtmlResponse_invalid(errormessage: str):
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><link rel="shortcut icon" href="data:"><title>TT-Robby</title></head><body>{errormessage}</body></html>"""
#path_regexes = ['/ball-driver/motors/(?<number>)/speed', 'GET', 'bd_motor_speed'] # this approach is too slow, so forget it for now
class WebServer:
    def get_path_tree(self, controller: RobbyController.RobbyController, method: str) -> tuple[dict, bool]:
        # POST is used to operate the machine, incl. triggering test routines for calibration.
        # POST differs from PUT in that no additional data is sent in the body of the request
        if method == 'POST':
            return {
                'api': {
                    'v1':{
                        'system': {
                            'start_playing': controller._start_playing,
                            'stop_playing': controller._stop_playing,
                            'save_settings': controller._save_settings,
                            'load_settings': controller._load_settings,
                        },
                        'balldrivers': {
                            '^[0-9]+$': {
                                'start': lambda bd: controller.API.bd_start_motors(int(bd), 50), # start motors with 50% speed
                                'stop': lambda bd: controller.API.bd_stop_motors(int(bd)), 
                                'motors': {
                                    '^[0-9]+$': {
                                        'start': lambda bd, m: controller.API.bd_set_motor_speed(int(bd), int(m), 50), # start motor with 50% speed
                                        'stop': lambda bd, m: controller.API.bd_set_motor_speed(int(bd), int(m), 0),
                                    },
                                },
                            },
                        },
                        'ballstirrers': {
                            '^[0-9]+$': {
                                'start': lambda bs: controller.API.bs_start(int(bs)),
                                'stop': lambda bs: controller.API.bs_stop(int(bs)),
                                'motors': {
                                    '^[0-9]+$': {
                                        'start': lambda bd, m: controller.API.bs_motor_start(int(bd), int(m)),
                                        'stop': lambda bd, m: controller.API.bs_motor_stop(int(bd), int(m)),
                                    },
                                },
                            },
                        },
                        'ballfeeders': {
                            '^[0-9]+$': {
                                'dispense': lambda bf: controller.ball_feeders[int(bf)].dispense(),
                                'prepare': lambda bf: controller.ball_feeders[int(bf)].prepare_after_mount(),
                                'stop': lambda bf: controller.ball_feeders[int(bf)].stop(),
                                'motors': {
                                    '^[0-9]+$': {
                                        'rotate': lambda bf, m, data: controller.API.bf_motor_rotate(int(bf), int(m), 5.0),
                                        'stop': lambda bf, m: controller.API.bf_motor_stop(int(bf), int(m)),
                                    }    
                                },
                            },
                        },
                    }
                }
            }, False
        # PUT is used to modify data for existing resources, which can be both, configs and status data
        if method == 'PUT':
            return {
                'api': {
                    'v1':{
                        'system': {
                            'config': lambda req_data: controller.adopt_general_settings(req_data['data']['settings']),
                            'mode': lambda data: controller.request_mode_change(data), # switch mode to operation or configuration
                        },
                        'balldrivers': {
                            '^[0-9]+$': {
                                'motors': {
                                    '^[0-9]+$': {
                                        'config': lambda bd, m, data: self.set_bd_motor_config(controller, int(bd), int(m), data),
                                        'speed': lambda bd, m, data: self.set_bd_motor_speed(controller, int(bd), int(m), data),
                                        '/default/': lambda bd, m, data: self.set_bd_motor_speed(controller, int(bd), int(m), data),
                                    },
                                    'all': {
                                        'speed': lambda bd, data: self.set_bd_motor_speed(controller, int(bd), -1, data),
                                        '/default/': lambda bd, data: self.set_bd_motor_speed(controller, int(bd), -1, data),
                                    },
                                    #'/default/': lambda: controller.ballDriver.getInformation(),
                                },
                                #'/default/': lambda: controller.ballDriver.getInformation(),
                            },
                        },
                        'ballstirrers': {
                            '^[0-9]+$': {
                                'config': lambda bs, data: controller.ball_stirrers[int(bs)].setConfigData(data),
                                'status': lambda bf: {},
                                '/default/': lambda bs: {},
                            },
                        },
                        'ballfeeders': {
                            '^[0-9]+$': {
                                'motors': {
                                    '^[0-9]+$': {
                                        'rotate': lambda bf, m, data: controller.API.bf_motor_rotate(int(bf), int(m), float(data['angle'])),
                                        'config': lambda bf, data: controller.ball_feeders[int(bf)].setConfigData(data),
                                        'status': lambda bf: {},
                                        '/default/': lambda bf: {},
                                    },
                                },
                            },
                        },
                    }
                }
            }, True
        if method == 'GET':
            return {
                'api': {
                    'v1':{
                        'system': {
                            'config': controller.getConfigData,
                            'status': controller.getStatusData,
                            '/default/': controller.getStatusData,
                        },
                        'balldrivers': {
                            '^[0-9]+$': {
                                'motors': {
                                    '^[0-9]+$': {
                                        'speed': lambda bd, m: {'speed': controller.ballDrivers[int(bd)].motors[int(m)].speed},
                                        'config': lambda bd, m: controller.ballDrivers[int(bd)].motors[int(m)].getConfigData(),
                                        'status': lambda bd, m: controller.ballDrivers[int(bd)].motors[int(m)].getStatusData(),
                                        '/default/': lambda bd, m: controller.ballDrivers[int(bd)].motors[int(m)].getStatusData(),
                                    },
                                    'all': {
                                        'config': lambda bd: list([m.getConfigData() for m in controller.ballDrivers[int(bd)].motors]),
                                        'status': lambda bd: list([m.getStatusData() for m in controller.ballDrivers[int(bd)].motors]),
                                        'speed': lambda bd: list([{'motor_number': m.speed} for m in controller.ballDrivers[int(bd)].motors]),
                                        '/default/': lambda bd: list([m.getStatusData() for m in controller.ballDrivers[int(bd)].motors]),
                                    },
                                    '/default/': lambda bd: controller.ballDrivers[int(bd)].getStatusData(),
                                },
                                'config': lambda bd: controller.ballDrivers[int(bd)].getConfigData(),
                                'status': lambda bd: controller.ballDrivers[int(bd)].getStatusData(),
                                '/default/': lambda bd: controller.ballDrivers[int(bd)].getStatusData(),
                            },
                            'config': lambda: [bd.getConfigData() for bd in controller.ballDrivers],
                        },
                        'ballstirrers': {
                            '^[0-9]+$': {
                                'config': lambda bs: controller.ball_stirrers[int(bs)].getConfigData(),
                                'status': lambda bs: controller.ball_stirrers[int(bs)].getStatusData(),
                                '/default/': lambda bs: controller.ball_stirrers[int(bs)].getStatusData(),
                            },
                            'config': lambda: [bs.getConfigData() for bs in controller.ball_stirrers],
                        },
                        'ballfeeders': {
                            '^[0-9]+$': {
                                'config': lambda bf: controller.ball_feeders[int(bf)].getConfigData(),
                                'status': lambda bf: controller.ball_feeders[int(bf)].getStatusData(),
                                '/default/': lambda bf: controller.ball_feeders[int(bf)].getStatusData(),
                            },
                            'config': lambda: [bf.getConfigData() for bf in controller.ball_feeders],
                        },
                        'machinerotators': {
                            '^[0-9]+$': {
                                'config': lambda bf: controller.API.get_machine_rotator_config(int(bf)),
                                #'status': lambda bf: controller.API.get_machine_rotator_status(int(bf)),
                                '/default/': lambda bf: controller.API.get_machine_rotator_config(int(bf)),
                            },
                            'config': lambda: controller.API.get_machine_rotator_config(-1),
                        },
                    },
                },
            }, False
        return {}, False

    """This class provides the features for receiving commands via http REST API calls"""
    total_mem = gc.mem_free()+gc.mem_alloc()

    def __init__(self, port=80, debug: Union[bool, None]=None):
        print("Initializing WebServer...")
        if not hasattr(network, "WLAN"):
            raise Exception("Pico apparently has no WLAN module! Aborting WebServer...")
        self.debug = debug
        self._load_wifi_secrets('/wifi.secrets')
        if self.wlan_name and self.wlan_secret:
            self.net = self.connectWifi(self.wlan_name, self.wlan_secret)
        else:
            self.net = None
            print("WLAN connection not or not fully specified!")
        if not self.net:
            print("Could not connect to wifi.") # don't care...
        else:
            print("WebServer running on ", self.net.ifconfig()[0], " (" + network.hostname() + ")")

        self.server = None
        addr = socket.getaddrinfo('0.0.0.0', port)[0][-1]
        self.server = socket.socket()
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind(addr)
        self.server.listen()
        if self.debug:
            print("Server listener set on ", addr)
        print("Free memory: ", gc.mem_free(), "/", self.total_mem)

    @classmethod
    def setHostname(cls, hostname: str):
        try:
            network.hostname(hostname)
        except Exception as e:
            InputDataException(f"Could not set hostname to '{hostname}': '{str(e)}'")

    def _load_wifi_secrets(self, path: str):
        try:
            if self.debug:
                print(f"Loading wifi secrets from file '{path}'.")
            with open(path,'r') as f:
                sec = json.load(f)
            self.wlan_name = sec.get('SSID')
            self.wlan_secret = sec.get('KEY')
        except Exception as e:
            print(f"Cannot load secrets from file '{path}': {str(e)}")
            #Exception(f"Cannot load settings from file '{path}': {str(e)}")

    def _save_wifi_secrets(self, path: str):
        try:
            if self.debug:
                print(f"Saving wifi secrets to file '{path}'.")
            with open(path,'w') as f:
                json.dump({'SSID': self.wlan_name, 'KEY': self.wlan_secret}, f)
        except Exception as e:
            Exception(f"Cannot save settings to file '{path}': {str(e)}")

    def run(self, controller: RobbyController.RobbyController):
        """Starts the listener to react to incoming requests"""
        if self.server is None:
            raise ImplementationException("Server is not initialized!") # Might occur when accidentially overwriting .server after init.
        if controller is None:
            raise ImplementationException("Controller must not be None!")
        if self.debug:
            print(f"Webserver up and running.")
        while True:
            try:
                conn, addr = self.server.accept()
                print("HTTP-Request received from ", addr)
                request = conn.recv(1024).decode()
                if request == '':
                    # skip keep_alive requests
                    if self.debug:
                        print("Ignoring empty request.")
                    continue
                # HTTP-Request anzeigen
                if self.debug:
                    print("Request:", request)
                header, body = str(request).split('\r\n\r\n', 1)
                if self.debug:
                    print(f"{header=}\n{body=}")
                req_header_lines = header.split()
                if len(req_header_lines) < 3:
                    raise Exception("Invalid request: Too few parts!")
                method = req_header_lines[0].upper()
                if method == 'OPTIONS':
                    # react on CORS request: Erlaubt alle Quellen, bestimmte Methoden, bestimmte Header
                    response = "HTTP/1.1 200 OK\r\nAccess-Control-Allow-Origin: *\r\nAccess-Control-Allow-Methods: GET, POST, PUT, OPTIONS\r\nAccess-Control-Allow-Headers: Content-Type\r\nContent-Length: 0\r\n\r\n"
                    conn.send(response.encode())
                if method not in ('GET', 'PUT', 'POST'):
                    if self.debug:
                        print(f"Http method not supported: {req_header_lines[0]}")
                    response = getHtmlResponse_invalid(f"Http method not supported: {req_header_lines[0]}")
                    rcode = 405
                path = req_header_lines[1]
                if path.startswith('/api/'):
                    try:
                        data = self.walk_path(method, path, controller, body)
                        response = json.dumps(data)
                        rcode = 200
                    except InputDataException as e:
                        response = getHtmlResponse_invalid(str(e))
                        rcode = 406
                    except ImplementationException as e:
                        response = getHtmlResponse_invalid(str(e))
                        rcode = 500
                    except Exception as e:
                        response = getHtmlResponse_invalid(str(e))
                        rcode = 500
                else:
                    response = getHtmlResponse_invalid(f'No valid path specified for API: {path}')
                    rcode = 404
                # HTTP-Response senden
                if rcode == 200:
                    # send json
                    conn.send(f'HTTP/1.0 {rcode} OK\r\nContent-type: text/json\r\nAccess-Control-Allow-Origin: *\r\nAccess-Control-Allow-Methods: GET, POST, PUT, OPTIONS\r\nAccess-Control-Allow-Headers: Content-Type\r\n\r\n')
                else:
                    # send html
                    # IMPROVE: also send errors as json, only calls outside /api path should result in html
                    conn.send(f'HTTP/1.0 {rcode} OK\r\nContent-type: text/html\r\nAccess-Control-Allow-Origin: *\r\nAccess-Control-Allow-Methods: GET, POST, PUT, OPTIONS\r\nAccess-Control-Allow-Headers: Content-Type\r\n\r\n')
                conn.send(response)
                conn.close()
                if self.debug:
                    print('Sent HTTP-Response')
                print("Free memory: ", gc.mem_free(), "/", self.total_mem)
            except OSError as e:
                break
            except (KeyboardInterrupt):
                break
        try: 
            conn.close()
        except NameError: 
            pass
        self.server.close()
        print('Server shut down')

    def connectWifi(self, networkname, secret):
        net = None
        try:

            # Country settings
            #network.country('DE')
            #network.hostname('htagent')

            # Operate as client
            net = network.WLAN(network.STA_IF)

            # activate interface
            net.active(True)

            # connect
            net.connect(networkname, secret)

            # Wait until connected
            print(f"Connecting to {networkname}...")
            while not net.isconnected() and net.status() >= 0:
                time.sleep(1)
            print('Successfully connected:', net.status())
            return net
        except Exception as e:
            print(f"ERROR when connecting to {networkname}:", e)
            return net

    def set_bd_motor_speed(self, controller: RobbyController.RobbyController, bd_number: int, motor_index: int, data: dict):
        if self.debug:
            print(f"set_bd_motor_speed() called for {bd_number}-{motor_index} with {data=}...")
        ret = ''
        if motor_index < 0:
            for i in range(len(controller.ballDrivers[bd_number].motors)):
                if ret:
                    ret += '\n'
                ret += self.set_bd_motor_speed(controller, bd_number, i, data)
            return ret
        try:
            spd = data.get('speed')
            if spd is None:
                ret = f"ERROR when setting speed of motor {bd_number}-{motor_index}: Element 'speed' not provided in data!"
            else:
                controller.ballDrivers[bd_number].motors[motor_index].set_speed(int(spd))
        except Exception as e:
            ret = f"ERROR when setting speed of motor {motor_index}: {e}"
        return ret
    def set_bd_motor_config(self, controller: RobbyController.RobbyController, bd_number: int, motor_index: int, data: dict):
        if self.debug:
            print(f"set_bd_motor_config() called for {bd_number}-{motor_index} with {data=}...")
        ret = ''
        if motor_index < 0:
            for i in range(len(controller.ballDrivers[bd_number].motors)):
                if ret:
                    ret += '\n'
                ret += self.set_bd_motor_config(controller, bd_number, i, data)
            return ret
        try:
            controller.ballDrivers[bd_number].motors[motor_index].setConfigData(data)
        except Exception as e:
            ret = f"ERROR when setting config of motor {bd_number}-{motor_index}: {e}"
        return ret

    def assign(self, target, data) -> dict:
        try:
            target = data
            return {'result': 'OK'}
        except Exception as e:
            print("Exception in assignment: ", e)
            return {'result': f'{e}'}

    def build_response_body(self, data, errors: list) -> dict:
        """Build the whole API response body from the specified elements."""
        ret = {}
        ret['data'] = (data if data else [])
        if errors:
            ret['errors'] = errors
        return ret

    def walk_path(self, method: str, path: str, controller: RobbyController.RobbyController, req_data = None):
        """Walk through the search tree with the specified path and finally call the according API method."""
        # Searchtree provides the API methods to call for the specified path. The keys in the tree can contain regexes; they must start with ^ and end with $.
        # The values in the tree are either subtrees (type dict) or methods (callable, returning the API response as dictionary).
        # The actually specified path elements for regex levels (type str) are all passed to the callable as positional arguments in the order they occur in the path.
        # When no identical key is found in a path level then the regexes are tried in sequence, i.e. they should be ordered from more specific to less specific (if applicable - and only relevant within the same path level).
        # The number of parameters for the callables must at least be the same as the dynamic levels in the path (data parameter may be present additionally, e.g. for PUT).
        # Key '/default/' is used in the dict to specify an API method to call if the last level has been omitted from the specified path (i.e. the path is shorter).
        if self.debug:
            print(f"walk_path({method=}, {path=}, {req_data=}) started...")
        # POST is mainly used to trigger actions without additional need for data (will be subject to change, e.g. when moving pusher for a specific distance)
        path_levels = path.split('/')
        tree, contains_data = self.get_path_tree(controller, method)
        f_delegate = None
        f_params = []
        path_level = 0
        while tree is not None:
            # get tree for current path level
            lvltxt = ''
            while lvltxt == '':
                if path_level >= len(path_levels):
                    # check for default function at this level
                    lvltxt = '/default/'
                else:
                    lvltxt = path_levels[path_level]
                    if lvltxt.strip() == '':
                        path_level += 1
            subtree = tree.get(lvltxt)
            if subtree is None:
                # maybe regex? check all keys
                if self.debug:
                    print(f"{lvltxt=} not found in {tree.keys()}.\nChecking for matching regex...")
                for key in tree.keys():
                    if key[0] == '^' and key[-1] == '$':
                        if self.debug:
                            print(f"RegEx located: {key}")
                        # check keys for a match
                        m = re.match(key, lvltxt)
                        if self.debug:
                            print(f"RegEx matched: {m}")
                        if m is not None:
                            # use that subtree
                            subtree = tree[key]
                            # and store the lvltxt as parameter
                            f_params.append(lvltxt) # do we really need that or shall we take it from the path_levels in the end?
            if subtree is not None:
                if type(subtree) == dict:
                    # found an actual subtree, so continue with that
                    tree = subtree
                    path_level += 1
                elif callable(subtree):
                    # found a function, so return it
                    f_delegate = subtree
                    tree = None
                else:
                    raise ImplementationException(f"Implementation Error: API path {method} {path} not implemented properly!")
            else:
                # not a valid api call
                raise InputDataException(f"{method} {path} is not a valid API path!")
        data = None
        errors = []
        if f_delegate:
            try:
                if self.debug:
                    print(f"path parameters determined: {f_params}")
                    print(f"{contains_data=}, {req_data=}")
                if contains_data and req_data is not None:
                    if self.debug:
                        print(f"calling delegate with {f_params=}, {req_data=}")
                    try:
                        data_dict = json.loads(req_data)
                    except Exception as e:
                        raise InputDataException(f"Data could not be parsed as json: {e}")
                    tmp = f_delegate(*f_params, data_dict)
                else:
                    if self.debug:
                        print(f"calling delegate with {f_params=}")
                    tmp = f_delegate(*f_params)
                if self.debug:
                    print(f"result from API-method: {tmp}")
                if tmp:
                    # TODO: This was changed into all paths returning the original data. If that's ok, remove the type checks!
                    if isinstance(tmp, (bool, str, int, float)):
                        # use primitive return types as data and add status information
                        data = tmp
                    if isinstance(tmp, list):
                        # append to existing data
                        data = tmp
                    else:
                        data = tmp
                if self.debug:
                    print(f"return {data=}")
            except Exception as e:
                print(f"Error: Could not execute API-method for {method} {path}: {str(e)}")
                errors.append(f"Could not execute API-method for {method} {path}: {str(e)}")
        else:
            raise ImplementationException(f"API method is None for {method} {path}!")
        ret = self.build_response_body(data, errors)
        return ret
    
if __name__ == "__main__":
    server = WebServer(80, debug=True)
    controller = RobbyController.RobbyController()
    controller._prepare_after_mount()
    server.run(controller=controller)
    controller._stop_playing()

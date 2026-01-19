#!/usr/bin/env python3
"""
This is a program for controlling video devices remotely from a web interface. A JSON file is used to define device connections and command sequences to perform complex actions. It is stateless meaning it cannot represent data from the devices (ex, a volume slider is not possible), but this is intentional to make it easier to use from multiple client devices simultaneously.

Basic usage is to just launch it with a configuration file:

    video-route -c config-sample.json

"""

# Python System
import argparse
import datetime
import sys
import re
import os
import time
import json
from pprint import pprint
import asyncio
import signal
from multiprocessing import Process


# External Modules
try:
    from flask import Flask
    from flask import Response
    from flask import request
    from flask import send_file
    from flask import redirect
    from flask import make_response
    from flask import send_from_directory
except Exception as e:
        print("Need to install Python module [flask]")
        sys.exit(1)

# JSON doesn't support all escape sequences this is a substitute list to add some
json_codes = {
    "#CR":"\r",
    "#ESC":"\x1b"
}

def serialByName(name):
    """
    This is a wrapper to allow the user to specify serial devices by their USB name or ID and path.

    You can see all serial device information for connected devices by running:

        video-route -S

    :param name: The name or ID and path of the serial device
    :return: returns path to serial device or value of name if no match found
    """

    # Assume if /dev/ in string a normal serial path was provided
    if "/dev/" in name:
        return name

    for port in serial.tools.list_ports.comports():
        # Match by name
        if port[1] == name:
            return port[0]
        # Match by ID and path
        if port[2] == name:
            return port[0]

    # Return given value if no matches were found
    return name



async def telnet_commands(ip,cmds,skip=0,delay=0,port=23):
    """
    Generic telnet wrapper for use with multiple devices. This exists to wrap the async requirement but also so that a single connection can be established for all needed commands.


    :param ip: IP for telnet server
    :param cmds: List of strings for all commands to execute
    :param skip: Number of lines to read and discard when connecting to server before issuing commands
    :param delay: Time in seconds to wait before sending next command
    :param port: Port for telnet server
    :return: returns response from last command
    """
    reader, writer = await telnetlib3.open_connection(ip, 23)

    while skip:
        inp = await reader.readuntil()
        skip-=1

    response = None
    for cmd in cmds:
        for key, value in json_codes.items():
            cmd = cmd.replace(key,value)
        writer.write(cmd)
        response = await reader.readuntil()
        print(response.decode("ascii"))
        time.sleep(delay)

    return response.decode("ascii")


class WebInterface(object):
    """
    Web frontend to hardware access. Generates web page based on user JSON and responds to actions by passing commands to hardware.
    """

    def __init__(self,args):
        """
        Construct a new 'Foo' object.

        :param args: argument values from program start
        :return: returns nothing
        """

        # Find location of this file and use it as the base path for the web server
        self.host_dir=os.path.realpath(__file__).replace(os.path.basename(__file__),"")
        self.app = Flask("Video Route")
        # Logging Options
        #self.app.logger.disabled = True
        #log = logging.getLogger('werkzeug')
        #log.disabled = True

        # Static content
        self.app.static_folder=self.host_dir+"http/static"
        self.app.static_url_path='/static/'

        # Define routes in class to use with flask
        self.app.add_url_rule('/','home', self.index)
        self.app.add_url_rule('/system','system', self.web_system,methods=["POST"])

        # Setup based on arguments
        self.host = args.ip
        self.port = args.port
        self.config_file = args.config
        self.config_init = args.reset_skip

        # Define map for all supported device types for matching to JSON
        self.video_controllers = {}
        self.video_controllers["serial"] = self.cmd_serial
        self.video_controllers["telnet"] = self.cmd_telnet
        self.video_controllers["http_get"] = self.cmd_http_get
        self.video_controllers["atem"] = self.cmd_atem
        self.video_controllers["obs"] = self.cmd_obs

        # Module load information for each device type
        self.controller_modules = {}
        for video_controller, function in self.video_controllers.items():
            self.controller_modules[video_controller] = False

        # Initial config load
        self.load_config()


    def load_config(self,config_file=None):
        """
        Load config file used to set connections to devices and define web interface.

        When a new device type is loaded, if it has any module dependencies these are imported for the first time here as globals. This prevents users who don't have some less common devices, such as the Blackmagic Atem, from needed to install the dependencies for those if they won't be using them.

        :param config_file: The path to the JSON configuration file.
        :return: returns nothing
        """
        # Use instance file path if not provided
        if config_file is not None:
            self.config_file = config_file

        # If file exists, load it
        if self.config_file is not None and os.path.exists(self.config_file):
            print("Reading from config")
            with open(self.config_file, newline='') as jsonfile:
                self.config=json.load(jsonfile)
        else:
            # No file provided or did not exist, warn user on web interface
            self.config={
                "video_controllers":{
                },
                "sources":{
                    "blank":{
                        "name":"No Configuration file Provided",
                        "icon":"smpte",
                        "description":"You have started the video routing program without a configuration file. You will need to create one and pass it as a parameter to the -c argument when starting the program"
                        }
                    }
            }

        # Skip initialization commands or not
        if not self.config_init:
            for key, value in self.config["video_controllers"].items():
                if "cmd_init" in value:
                    self.video_controllers[value["type"]](value["cmd_init"],value)

            self.config_init=True

        # Load modules for all defined device types in JSON config
        for key, value in self.config["video_controllers"].items():
            if not self.controller_modules[value["type"]]:
                match value["type"]:
                    case "serial":
                        try:
                            global serial
                            import serial
                            import serial.tools.list_ports
                            self.controller_modules["serial"] = True

                        except Exception as e:
                            print("Need to install Python module [pyserial]")
                            sys.exit(1)
                    case "telnet":
                        try:
                            global telnetlib3
                            import telnetlib3
                            self.controller_modules["telnet"] = True
                        except Exception as e:
                            print("Need to install Python module [telnetlib3]")
                            sys.exit(1)
                    case "http_get":

                        global request_url
                        global parse
                        from urllib import request as request_url, parse
                        self.controller_modules["http_get"] = True
                    case "atem":

                        try:
                            global PyATEMMax
                            import PyATEMMax
                            self.controller_modules["atem"] = True
                        except Exception as e:
                            print("Need to install Python module [PyATEMMax]")
                            sys.exit(1)
                    case "obs":

                        try:
                            global obs
                            import obsws_python as obs
                            self.controller_modules["obs"] = True
                        except Exception as e:
                            print("Need to install Python module [obsws-python]")
                            sys.exit(1)


    async def start(self):
        """
        Start web server in Process thread

        :return: returns nothing
        """
        print("Starting Flask")
        self.web_thread = Process(target=self.app.run,
            kwargs={
                "host":self.host,
                "port":self.port,
                "debug":False,
                "use_reloader":False
                }
            )
        self.web_thread.start()

    def stop(self):
        """
        Stop web server in Process thread

        :return: returns nothing
        """
        if hasattr(self, "web_thread") and self.web_thread is not None:
            self.web_thread.terminate()
            self.web_thread.join()

    def cmd_serial(self,cmds,config):
        """
        Send commands to serial device.

        :param cmds: Commands as list of strings to send
        :param config: Device controller configuration
        :return: returns nothing
        """
        line_end=config["line_end"] if "line_end" in config else ""
        cmd_delay=config["cmd_delay"] if "cmd_delay" in config else 0
        try:
            serial_interface = serial.Serial(serialByName(config["serial"]),config["baud"],timeout=30,parity=config["parity"])
            for cmd in cmds:
                for key, value in json_codes.items():
                    cmd = cmd.replace(key,value)
                serial_interface.write( bytes(cmd+line_end,'ascii',errors='ignore') )
                print(bytes(cmd+line_end,'ascii',errors='ignore'))
                time.sleep(cmd_delay)

        except Exception as e:
            name=config["name"] if "name" in config else config["type"]
            print(f"Error with device [{name}]:" + repr(e))


    def cmd_http_get(self,cmds,config):
        """
        Send commands to HTTP endpoint as GET URL parameter.

        :param cmds: Commands as list of strings to send
        :param config: Device controller configuration
        :return: returns nothing
        """
        cmd_delay=config["cmd_delay"] if "cmd_delay" in config else 0
        try:
            for cmd in cmds:
                for key, value in json_codes.items():
                    cmd = cmd.replace(key,value)
                endpoint=f'http://{config["ip"]}{config["uri"]}{cmd}'
                req =  request_url.Request(endpoint)
                resp = request_url.urlopen(req)
                time.sleep(cmd_delay)

        except Exception as e:
            name=config["name"] if "name" in config else config["type"]
            print(f"Error with device [{name}]:" + repr(e))


    def cmd_telnet(self,cmds,config):
        """
        Send commands to telnet server.

        :param cmds: Commands as list of strings to send
        :param config: Device controller configuration
        :return: returns nothing
        """
        try:
            cmd_delay=config["cmd_delay"] if "cmd_delay" in config else 0
            port=config["port"] if "port" in config else 23
            connection_skip=config["connection_skip"] if "connection_skip" in config else 0
            asyncio.run(telnet_commands(config["ip"],cmds,skip=connection_skip,delay=cmd_delay,port=port))

        except Exception as e:
            name=config["name"] if "name" in config else config["type"]
            print(f"Error with device [{name}]:" + repr(e))


    def cmd_atem(self,cmds,config):
        """
        Send commands to ATEM controller over network.

        :param cmds: Commands as list of of dicts with function name as key and parameters as value
        :param config: Device controller configuration
        :return: returns nothing
        """
        cmd_delay=config["cmd_delay"] if "cmd_delay" in config else 0
        try:
            switcher = PyATEMMax.ATEMMax()
            print(f'Atem Connect: {config["ip"]}')
            switcher.connect(config["ip"])
            switcher.waitForConnection()
            for cmd in cmds:
                for function, p in cmd.items():
                    if hasattr(switcher,function):
                        getattr(switcher,function)(*p)
                    else:
                        print(f"Error with device [{name}]: OBS has no function [{function}]")
                time.sleep(cmd_delay)
            switcher.disconnect()

        except Exception as e:
            name=config["name"] if "name" in config else config["type"]
            print(f"Error with device [{name}]:" + repr(e))


    def cmd_obs(self,cmds,config):
        """
        Send commands to OBS using web sockets.

        :param cmds: Commands as list of of dicts with function name as key and parameters as value
        :param config: Device controller configuration
        :return: returns nothing
        """
        cmd_delay=config["cmd_delay"] if "cmd_delay" in config else 0
        name=config["name"] if "name" in config else config["type"]
        try:
            client = obs.ReqClient(host=config["ip"], port=config["port"], password=config["password"], timeout=config["timeout"])
            for cmd in cmds:
                for function, p in cmd.items():
                    if hasattr(client,function):
                        data =self.function_chain(client,function,p)
                        if data is not None:
                            pprint(getattr(data,data.attrs()[0]))
                    else:
                        print(f"Error with device [{name}]: OBS has no function [{function}]")
                time.sleep(cmd_delay)

        except Exception as e:
            print(f"Error with device [{name}]:" + repr(e))


    def function_chain(self,client,function,p):
        """
        Recursively calls functions to pull data from client to build parent functions

        :param client: Base object functions will be called on
        :param function: base function
        :return: returns retsult of function
        """

        if hasattr(client,function):
            processed=[]
            for parameter in p:
                if isinstance(parameter, dict):
                    # Parameter is also a function
                    call=None
                    attr=None
                    resp=None
                    for sub_function, sub_p in parameter.items():
                        if isinstance(sub_p, dict):
                            # Parameter to pull from function specified
                            attr=sub_function
                            for sub2_function, sub2_p in sub_p.items():
                                call=sub2_function
                                resp = self.function_chain(client,sub2_function,sub2_p)
                        else:
                            # Return first attribute
                            call=sub_function
                            resp = self.function_chain(client,sub_function,sub_p)
                            attr=resp.attrs()[0]
                        processed.append(getattr(resp,attr))
                        print(f'{call} returned: {parameter}')
                else:
                    processed.append(parameter)

            print(f'{function} calling with:')
            pprint(processed)
            data = getattr(client,function)(*processed)
            return data
        else:
            print(f"Error [{function}] doesn't exist")


# Endpoints

    def index(self):
        """
        Base HTML for web front end. Defines paths to common resources and calls to build main source list.

        :return: returns generated HTML as string
        """
        self.load_config()
        # HTML starts
        output=f'''
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=0.7, maximum-scale=0.7, user-scalable=no" />
<meta name="HandheldFriendly" content="true" />
<script>
function system(event) {{
    if ("source" in event.target.attributes)
    {{
        data={{"source":event.target.attributes.source.nodeValue}}
    }}
	fetch("/system", {{
		method: 'post',
	   headers: {{
		   "Content-Type": "application/json",
		   'Accept':'application/json'
	   }},
	   body: JSON.stringify(data),
	}}).then(() => {{
		// Do Nothing
	}});
}};
</script>
<link rel="stylesheet" type="text/css" href="/static/site/style.css" ></style>
<link rel="stylesheet" type="text/css" href="/static/user.css" ></style>
</head>
<body>
<div class="sources" >
'''
        output+=self.build_sources(self.config["sources"])

        output+=f'''
</div>
</body>
<script type="text/javascript" src="/static/user.js"></script>
</html>
'''
        return output


    def build_sources(self,source,prefix=""):
        """
        Builds user front end based on JSON config file. Reloads config every time to allow realtime adjustment of JSON during initial setup.

        Nested sources are generated as fieldsets and call this function recursively. This is the primary way of grouping related commands.

        Commands are not stored in JSON data, nested key paths are stored as a custom attribute which is used to walk the dictionary path in the function that parses the web client responses.

        :param source: Source data from JSON config
        :param prefix: Identifier prefix to use for un-nesting sources
        :return: returns generated HTML as string
        """
        output=""
        for key, value in source.items():

            # Define and custom user colors
            colors=""
            if "color" in value:
                colors+=f'color:{value["color"]};'
            if "background" in value :
                colors+=f'background-color:{value["background"]};'

            # Allow usage of built in images as icons
            if "icon" in value:
                match value["icon"]:
                    case "wide":
                        value["icon"] = "../site/video-wide.png"
                    case "full":
                        value["icon"] = "../site/video-full.png"
                    case "pixel":
                        value["icon"] = "../site/video-pixel.png"
                    case "crop":
                        value["icon"] = "../site/video-crop.png"
                    case "smpte":
                        value["icon"] = "../site/smpte.png"
                    case None:
                        value["icon"] = "../site/smpte.png"

            # If a dictionary is found it is a nested source list. Build a fieldset and recursively call this function again to build its sources.
            if isinstance(value, dict):
                if "sources" in value:
                    output+=f'''
    <fieldset class="group" style="{colors}">
    '''
                    # Hide fieldset by default if "hide" key is present and true
                    checked=""
                    if "hide" in value:
                        if value["hide"]:
                            checked="checked"

                    # Use "name" key as legend for fieldset
                    if "name" in value:
                        output+=f'''
        <input type=checkbox id="{prefix+key}" {checked}/>
        <legend><label for="{prefix+key}">{value["name"]}</label></legend>
    '''
                    output+=f'''
        <div class="sources">
    '''
                    # Add icon if provided with source attribute to make it clickable
                    if "icon" in value:

                        output+=f'''
                <div onclick="system(event)" class="button group-icon"><img src="/static/icons/{value["icon"]}" source="{prefix+key}"></div>
            '''
                    # Recursive call to build child sources
                    output+=self.build_sources(value["sources"],prefix+key+"|")

                    output+=f'''
        </div>
        '''
                    # Add description if provided
                    if "description" in value:
                        output+=f'''
        <div class="text-block" source="{prefix+key}">
            <p class="description" source="{prefix+key}">{value["description"]}</p>
        </div>
    '''

                    output+=f'''
    </fieldset>
    '''
                    continue

            # If a description is present, render source as inline-block
            if "description" in value:
                output+=f'''
    <div source="{prefix+key}" style="{colors}" onclick="system(event)" class="list">
    '''
            else:
                output+=f'''
    <div source="{prefix+key}" style="{colors}" onclick="system(event)" class="button">
    '''
            # Add icon
            if "icon" in value:
                    # Provided Image
                    output+=f'''
        <img src="/static/icons/{value["icon"]}" source="{prefix+key}">
    '''
            # Use div to group test if description provided
            if "description" in value:
                output+=f'''
        <div class="text-block" source="{prefix+key}">
    '''
            # Add name as header
            if "name" in value:
                output+=f'''
        <h3 class="name" source="{prefix+key}">{value["name"]}</h3>
    '''
            # Add description if provided
            if "description" in value:
                output+=f'''
        <p class="description" source="{prefix+key}">{value["description"]}</p>
        </div>
    '''
            output+=f'''
    </div>
    '''

        return output


    def web_system(self):
        """
        Endpoint handler for commands from web interface

        :return: returns generic response for HTTP
        """
        data = request.get_json()
        pprint(data)
        if "source" in data:
            self.parse_sources(data['source'], self.config["sources"])

        return "sure"


    def parse_sources(self, source, config):
        """
        Parses delimited source command identifier to run associated commands. Recursively calls self for nested sources.

        :param source: Source identifier string from web frontend
        :param config: Source list from config
        :return: returns nothing
        """

        if source.split("|")[0] in config:
            for key, value in config[source.split("|")[0]].items():

                if isinstance(value, dict):
                    self.parse_sources(source[len(source.split("|")[0])+1:], value)

                if key in self.config["video_controllers"] and self.config["video_controllers"][key]["type"] in self.video_controllers:
                    print(f'Configuring: {key}')
                    self.video_controllers[self.config["video_controllers"][key]["type"]](value,self.config["video_controllers"][key])


# ------ Async Server Handler ------
global loop_state
global server
loop_state = True
server = None


async def asyncLoop():
    """
    Blocking main loop to provide time for async tasks to run

    :return: returns nothing
    """
    print('Blocking main loop')
    global loop_state
    while loop_state:
        await asyncio.sleep(1)


def exit_handler(sig, frame):
    """
    Handle CTRL-C to gracefully end program and API connections

    :return: returns nothing"""
    global loop_state
    print('You pressed Ctrl+C!')
    loop_state = False
    server.stop()


async def startWeb(args):
    """
    Asynchronously start web interface

    :return: returns nothing
    """

    global server
    server = WebInterface(args)

    """ Start connections to async modules """

    # Setup CTRL-C signal to end programm
    signal.signal(signal.SIGINT, exit_handler)
    print('Press Ctrl+C to exit program')

    # Start async modules
    L = await asyncio.gather(
        server.start(),
        asyncLoop()
    )
# ------ Async Server Handler ------


def main():
    """
    Execute CLI start and process parameters

    :return: returns exit code
    """
    # Setup CLI arguments
    parser = argparse.ArgumentParser(
                    prog="video-route",
                    description='Web page remote for control video processors',
                    epilog='')
    parser.add_argument('-i', '--ip', help="Web server listening IP", default="0.0.0.0")
    parser.add_argument('-p', '--port', help="Web server listening port", default="5000")
    parser.add_argument('-c', '--config', help="JSON config file", default=None)
    parser.add_argument('-r', '--reset-skip', help="Do not re-initialize hardware", action='store_true')
    parser.add_argument('-S', '--serial-names', help="List serial port names", action='store_true')
    parser.add_argument('other', help="", default=None, nargs=argparse.REMAINDER)
    args = parser.parse_args()


    # Print out information for all connected serial devices and exit
    if args.serial_names:
        try:
            import serial
            import serial.tools.list_ports
            for port in serial.tools.list_ports.comports():
                if port[1] != "n/a":
                    print( f'[{port[0]}] by Name: [{port[1]}]' )
                    print( f'[{port[0]}] by ID and Path: [{port[2]}]' )
            sys.exit(0)
        except Exception as e:
            print("Need to install Python module [pyserial]")
            sys.exit(1)


    # Run web server
    asyncio.run(startWeb(args))
    sys.exit(0)


if __name__ == "__main__":
    # Run main if script called directly
    main()

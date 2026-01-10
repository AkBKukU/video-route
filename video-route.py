#!/usr/bin/env python3

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

# JSON doesn't support all escape sequences this is a substitute list to add them
json_codes = {
    "#CR":"\r",
    "#ESC":"\x1b"
}

# External Modules
def serialByName(name):

    # Lazy wrap both
    if "/dev/" in name:
        return name

    for port in serial.tools.list_ports.comports():
        if port[1] == name:
            return port[0]

    # They know better probably
    return name



async def telnet_commands(ip,cmds,skip=0,delay=0):
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
    try:
        # External Modules
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
    """Web interface for managing rips

    """

    def __init__(self,args):

        self.host_dir=os.path.realpath(__file__).replace(os.path.basename(__file__),"")
        self.app = self.Flask("Video Route")
        #self.app.logger.disabled = True
        #log = logging.getLogger('werkzeug')
        #log.disabled = True

        # Static content
        self.app.static_folder=self.host_dir+"http/static"
        self.app.static_url_path='/static/'

        # Define routes in class to use with flask
        self.app.add_url_rule('/','home', self.index)
        # Define routes in class to use with flask
        self.app.add_url_rule('/system','system', self.web_system,methods=["POST"])

        self.host = args.ip
        self.port = args.port
        self.toggle = not args.split
        self.config_file = args.json
        self.config_init = args.reset_skip

        self.video_controllers = {}
        self.video_controllers["serial"] = self.cmd_serial
        self.video_controllers["telnet"] = self.cmd_telnet
        self.video_controllers["http_get"] = self.cmd_http_get
        self.video_controllers["atem"] = self.cmd_atem

        self.controller_modules = {}
        self.controller_modules["serial"] = False
        self.controller_modules["telnet"] = False
        self.controller_modules["http_get"] = False
        self.controller_modules["atem"] = False

        self.controller_atem = {}

        self.load_config()

    def load_config(self,config_file=None):
        if config_file is not None:
            self.config_file = config_file

        if self.config_file is not None and os.path.exists(self.config_file):
            print("Reading from config")
            with open(self.config_file, newline='') as jsonfile:
                self.config=json.load(jsonfile)
        else:
            self.config={
                "video_controllers":{
                },
                "sources":{}
            }

        if not self.config_init:
            for key, value in self.config["video_controllers"].items():
                if "cmd_init" in value:
                    self.video_controllers[value["type"]](value["cmd_init"],value)

            self.config_init=True


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

                        global request
                        global parse
                        from urllib import request, parse
                        self.controller_modules["http_get"] = True
                    case "atem":

                        global PyATEMMax
                        import PyATEMMax
                        self.controller_modules["atem"] = True


    async def start(self):
        """ Run Flask in a process thread that is non-blocking """
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
        """ Send SIGKILL and join thread to end Flask server """
        if hasattr(self, "web_thread") and self.web_thread is not None:
            self.web_thread.terminate()
            self.web_thread.join()
        if hasattr(self, "rip_thread"):
            self.rip_thread.terminate()
            self.rip_thread.join()

# Hardware commands
    def cmd_serial(self,cmds,config):
        line_end=config["line_end"] if "line_end" in config else ""
        try:
            serial_interface = serial.Serial(serialByName(config["serial"]),config["baud"],timeout=30,parity=config["parity"])
            for cmd in cmds:
                for key, value in json_codes.items():
                    cmd = cmd.replace(key,value)
                serial_interface.write( bytes(cmd+line_end,'ascii',errors='ignore') )
        except Exception as e:
            name=config["name"] if "name" in config else config["type"]
            print(f"Error with device [{name}]:" + repr(e))


    def cmd_http_get(self,cmds,config):
        cmd_delay=config["cmd_delay"] if "cmd_delay" in config else 0
        try:
            for cmd in cmds:
                for key, value in json_codes.items():
                    cmd = cmd.replace(key,value)
                endpoint=f'http://{config["ip"]}{config["uri"]}{cmd}'
                req =  request.Request(endpoint)
                resp = request.urlopen(req)
                time.sleep(cmd_delay)
        except Exception as e:
            name=config["name"] if "name" in config else config["type"]
            print(f"Error with device [{name}]:" + repr(e))


    def cmd_telnet(self,cmds,config):
        try:
            cmd_delay=config["cmd_delay"] if "cmd_delay" in config else 0
            connection_skip=config["connection_skip"] if "connection_skip" in config else 0
            asyncio.run(telnet_commands(config["ip"],cmds,skip=connection_skip,delay=cmd_delay))
        except Exception as e:
            name=config["name"] if "name" in config else config["type"]
            print(f"Error with device [{name}]:" + repr(e))


    def cmd_atem(self,cmds,config):
        try:
            switcher = PyATEMMax.ATEMMax()
            print(f'Atem Connect: {config["ip"]}')
            switcher.connect(config["ip"])
            switcher.waitForConnection()
            for cmd in cmds:
                for function, p in cmd.items():
                    print(f'Atem Function: {function}')
                    match function:
                        case "setProgramInputVideoSource":
                            print(f'{function}({p[0]},{p[1]})')
                            switcher.setProgramInputVideoSource(int(p[0]),int(p[1]))
                        case "setKeyerFillSource":
                            print(f'{function}({p[0]},{p[1]})')
                            switcher.setKeyerFillSource(int(p[0]),int(p[1]),int(p[2]))
            switcher.disconnect()


        except Exception as e:
            name=config["name"] if "name" in config else config["type"]
            print(f"Error with device [{name}]:" + repr(e))


# Endpoints

    def index(self):
        self.load_config()
        """ Simple class function to send HTML to browser """
        output=f'''
        <head>
	<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />
	<meta name="HandheldFriendly" content="true" />
	</head>
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
<body style="background-color:#111;">
<ul onclick="system(event)" >
'''
        output+=self.build_sources(self.config["sources"])

        output+=f'''
</ul>
</body>
'''
        return output


    def web_system(self):
        data = self.request.get_json()
        pprint(data)
        if "source" in data:
            self.parse_sources(data['source'], self.config["sources"])



        return "sure"

    def build_sources(self,source,prefix=""):
        output=""
        for key, value in source.items():

            if isinstance(value, dict):
                if "sources" in value:
                    output+=f'''
    <fieldset>
    '''
                    checked=""
                    if "hide" in value:
                        if value["hide"]:
                            checked="checked"
                    if "name" in value:
                        output+=f'''
        <input type=checkbox id="{prefix+key}" {checked}/>
        <legend><label for="{prefix+key}">{value["name"]}</label></legend>
        <ul>
    '''
                    # Image Setup
                    if "icon" in value:

                        output+=f'''
                <li class="buttons"><img src="/static/icons/{value["icon"]}" source="{prefix+key}"></li>
            '''
                    output+=self.build_sources(value["sources"],prefix+key+"|")

                    output+=f'''
        </ul>
        '''
                    # Text
                    if "description" in value:
                        output+=f'''
        <div class="text-block" source="{prefix+key}">
    '''

                    output+=f'''
    </fieldset>
    '''
                    continue

            if "description" in value:
                output+=f'''
    <li source="{prefix+key}" class="list">
    '''
            else:
                output+=f'''
    <li source="{prefix+key}" class="buttons">
    '''
            # Image Setup
            if "icon" in value:

                if value["icon"] == "wide":
                    value["icon"] = "../site/video-wide.png"
                if value["icon"] == "full":
                    value["icon"] = "../site/video-full.png"
                if value["icon"] == "pixel":
                    value["icon"] = "../site/video-pixel.png"
                if value["icon"] == "crop":
                    value["icon"] = "../site/video-crop.png"

                if value["icon"] is None:
                    # Stock Image
                    output+=f'''
        <img src="/static/site/smpte.png" source="{prefix+key}">
    '''
                else:
                    # Provided Image
                    output+=f'''
        <img src="/static/icons/{value["icon"]}" source="{prefix+key}">
    '''
            if "overlay" in value:
                # Provided Image with overlay
                output+=f'''
        <div class="overlay {value["overlay"]}" source="{prefix+key}"></div>
    '''
            # Text
            if "description" in value:
                output+=f'''
        <div class="text-block" source="{prefix+key}">
    '''
            if "name" in value:
                output+=f'''
        <h3 class="name" source="{prefix+key}">{value["name"]}</h3>
    '''
            if "description" in value:
                output+=f'''
        <p class="description" source="{prefix+key}">{value["description"]}</p>
        </div>
    '''
            output+=f'''
    </li>
    '''

        return output

    def parse_sources(self, source, config):

        if source.split("|")[0] in config:
            for key, value in config[source.split("|")[0]].items():

                if isinstance(value, dict):
                    print(key+" is dict")
                    self.parse_sources(source[len(source.split("|")[0])+1:], value)

                print(key+" not dict")
                if key in self.config["video_controllers"] and self.config["video_controllers"][key]["type"] in self.video_controllers:
                    self.video_controllers[self.config["video_controllers"][key]["type"]](value,self.config["video_controllers"][key])


# ------ Async Server Handler ------

global loop_state
global server
loop_state = True
server = None


async def asyncLoop():
    """ Blocking main loop to provide time for async tasks to run"""
    print('Blocking main loop')
    global loop_state
    while loop_state:
        await asyncio.sleep(1)


def exit_handler(sig, frame):
    """ Handle CTRL-C to gracefully end program and API connections """
    global loop_state
    print('You pressed Ctrl+C!')
    loop_state = False
    server.stop()


# ------ Async Server Handler ------



async def startWeb(args):

    # Internal Modules
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



def main():
    """ Execute as a CLI and process parameters

    """
    # Setup CLI arguments
    parser = argparse.ArgumentParser(
                    prog="video-route",
                    description='Web page remote for serial control of RT4K',
                    epilog='')
    parser.add_argument('-i', '--ip', help="Web server listening IP", default="0.0.0.0")
    parser.add_argument('-p', '--port', help="Web server listening IP", default="5003")
    parser.add_argument('-j', '--json', help="JSON config file", default=None)
    parser.add_argument('-r', '--reset-skip', help="Do not re-initialize hardware", action='store_true')
    parser.add_argument('-S', '--serial-names', help="List serial port names", action='store_true')
    parser.add_argument('-l', '--split', help="Split power button instead of toggle", action='store_true')
    parser.add_argument('other', help="", default=None, nargs=argparse.REMAINDER)
    args = parser.parse_args()

    if args.serial_names:
        for port in serial.tools.list_ports.comports():
            if port[1] != "n/a":
                print( port[0]+":"+port[1] )
        sys.exit(0)


    # Run web server
    asyncio.run(startWeb(args))
    sys.exit(0)



if __name__ == "__main__":
    main()

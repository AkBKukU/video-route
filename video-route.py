#!/usr/bin/env python3

# Python System
import argparse
import datetime
import sys
import re
import os
import json
from pprint import pprint
import asyncio
import signal
from multiprocessing import Process
from urllib import request, parse

# External Modules
try:
    import serial
    import serial.tools.list_ports

    def serialByName(name):

        # Lazy wrap both
        if "/dev/" in name:
            return name

        for port in serial.tools.list_ports.comports():
            if port[1] == name:
                return port[0]

        # They know better probably
        return name

except Exception as e:
    print("Need to install Python module [pyserial]")
    sys.exit(1)

# External Modules
try:
    import telnetlib3

    async def telnet_commands(ip,cmds,skip=0):
        reader, writer = await telnetlib3.open_connection(ip, 23)

        while skip:
            inp = await reader.readuntil()
            skip-=1

        codes = {
            "#CR":"\r",
            "#ESC":"\x1b"
            }

        response = None
        for cmd in cmds:
            for key, value in codes.items():
                cmd = cmd.replace(key,value)
            writer.write(cmd)
            response = await reader.readuntil()
            print(response.decode("ascii"))

        return response.decode("ascii")

except Exception as e:
    print("Need to install Python module [telnetlib3]")
    sys.exit(1)

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
        self.app = self.Flask("SRT Notes")
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

        self.video_controlers = {}
        self.video_controlers["crosspoint"] = self.cmd_crosspoint
        self.video_controlers["rt4k"] = self.cmd_rt4k
        self.video_controlers["in1606"] = self.cmd_in1606
        self.video_controlers["dvs510"] = self.cmd_dvs510

        if args.json is not None and os.path.exists(args.json):
            print("Reading from config")
            with open(args.json, newline='') as jsonfile:
                self.config=json.load(jsonfile)
        else:
            self.config={
                "video":{
                    "rt4k":None,
                    "crosspoint":None,
                    "in1606":None,
                    "dvs510":None,
                },
                "sources":{}
            }

        if not args.reset_skip and self.config["video"]["crosspoint"] is not None:
            self.cmd_crosspoint("\x1bZXXX")



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

    def cmd_crosspoint(self,cmds):
        cross = serial.Serial(serialByName(self.config["video"]["crosspoint"]),9600,timeout=30,parity=serial.PARITY_NONE)
        for cmd in cmds:
            cross.write( bytes(cmd,'ascii',errors='ignore') )


    def cmd_rt4k(self,cmds):
        rt4k = serial.Serial(serialByName(self.config["video"]["rt4k"]),115200,timeout=30,parity=serial.PARITY_NONE)
        for cmd in cmds:
            rt4k.write( bytes(cmd+"\n",'ascii',errors='ignore') )


    def cmd_dvs510(self,cmds):
        try:
            for cmd in cmds:
                endpoint=f'http://{self.config["video"]["dvs510"]}/?cmd={cmd}'
                req =  request.Request(endpoint)
                resp = request.urlopen(req)
        except Exception as e:
            pprint(e)


    def cmd_in1606(self,cmds):
        try:
            asyncio.run(telnet_commands(self.config["video"]["in1606"],cmds,skip=3))
        except Exception as e:
            pprint(e)

# Endpoints

    def index(self):
        """ Simple class function to send HTML to browser """
        output=f'''
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
<link rel="stylesheet" type="text/css" href="/static/style.css" ></style>
<body style="background-color:#111;">
<ul onclick="system(event)" >
'''
        for key, value in self.config["sources"].items():

            if "description" in value:
                output+=f'''
    <li source="{key}" class="list">
    '''
            else:
                output+=f'''
    <li source="{key}" class="buttons">
    '''
            # Image Setup
            if "icon" in value:

                if "overlay" in value:
                    # Provided Image with overlay
                    output+=f'''
        <img style="background: url('/static/{value["icon"]}');" src="/static/video-{value["overlay"]}.png" source="{key}">
    '''
                else:
                    # Provided Image
                    output+=f'''
        <img src="/static/{value["icon"]}" source="{key}">
    '''
            else:
                    # Stock Image
                    output+=f'''
        <img src="/static/smpte.png" source="{key}">
    '''
            # Text
            if "description" in value:
                output+=f'''
        <div class="text-block">
    '''
            if "name" in value:
                output+=f'''
        <h3 class="name">{value["name"]}</h3>
    '''
            if "description" in value:
                output+=f'''
        <p class="description">{value["description"]}</p>
        </div>
    '''
            output+=f'''
    </li>
    '''

        output+=f'''
</ul>
</body>
'''
        return output


    def web_system(self):
        data = self.request.get_json()
        pprint(data)
        if "source" in data:
            for key, value in self.config["sources"][data['source']].items():

                if key in self.video_controlers and self.config["video"][key] is not None:
                    self.video_controlers[key](value)


        return "sure"

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

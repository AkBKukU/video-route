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

except Exception as e:
    print("Need to install Python module [pyserial]")
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

    def __init__(self,ip,port,serial,split):

        self.host_dir=os.path.realpath(__file__).replace(os.path.basename(__file__),"")
        self.app = self.Flask("SRT Notes")
        self.app.logger.disabled = True
        #log = logging.getLogger('werkzeug')
        #log.disabled = True

        # Static content
        self.app.static_folder=self.host_dir+"http/static"
        self.app.static_url_path='/static/'

        # Define routes in class to use with flask
        self.app.add_url_rule('/','home', self.index)
        # Define routes in class to use with flask
        self.app.add_url_rule('/crosspoint','crosspoint', self.web_crosspoint,methods=["POST"])
        self.app.add_url_rule('/dvs510','dvs510', self.web_dvs510,methods=["POST"])
        self.app.add_url_rule('/in1606','in1606', self.web_in1606,methods=["POST"])
        self.app.add_url_rule('/system','system', self.web_system,methods=["POST"])

        self.host = ip
        self.port = port
        self.serial_crosspoint = serialByName("USB-Serial Controller")
        self.serial_rt4k = serialByName("FT232R USB UART - FT232R USB UART")
        self.toggle = not split

        self.config={
                "snes":{
                    "rt4k":"remote prof1",
                    "dvs510":3,
                    "crosspoint":["1*1!","1*2!","1*3!"]
                    },
                "n64":{
                    "rt4k":"remote prof2",
                    "dvs510":3,
                    "crosspoint":["2*1!","2*2!","2*3!"]
                    },
                "dc":{
                    "rt4k":"remote prof3",
                    "dvs510":5,
                    "crosspoint":["11*1!","3*2!","3*4!"]
                    },
            }

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


    def index(self):
        """ Simple class function to send HTML to browser """
        return f"""
<script>
function in1606(event) {{
	fetch("/in1606", {{
		method: 'post',
	   headers: {{
		   "Content-Type": "application/json",
		   'Accept':'application/json'
	   }},
	   body: JSON.stringify({{"cmd":event.target.attributes.name.nodeValue}}),
	}}).then(() => {{
		// Do Nothing
	}});
}};

function dvs510(event) {{
	fetch("/dvs510", {{
		method: 'post',
	   headers: {{
		   "Content-Type": "application/json",
		   'Accept':'application/json'
	   }},
	   body: JSON.stringify({{"cmd":event.target.attributes.name.nodeValue}}),
	}}).then(() => {{
		// Do Nothing
	}});
}};

function crosspoint(event) {{
	fetch("/crosspoint", {{
		method: 'post',
	   headers: {{
		   "Content-Type": "application/json",
		   'Accept':'application/json'
	   }},
	   body: JSON.stringify({{"cmd":event.target.attributes.name.nodeValue}}),
	}}).then(() => {{
		// Do Nothing
	}});
}};

function system(event) {{
	fetch("/system", {{
		method: 'post',
	   headers: {{
		   "Content-Type": "application/json",
		   'Accept':'application/json'
	   }},
	   body: JSON.stringify({{"cmd":event.target.attributes.name.nodeValue}}),
	}}).then(() => {{
		// Do Nothing
	}});
}};

</script>
<style>
.clearButton {{
    background-color: rgba(0, 0, 0, 0);
}}
</style>
<body style="background-color:#111;">
<a onclick="in1606(event)" >
<div name="4" class="clearButton">Retrotink 4K</div>
</a>
<a onclick="in1606(event)" >
<div name="3" class="clearButton">Extron Scaler</div>
</a>
<a onclick="system(event)" >
<div name="snes" class="clearButton">SNES</div>
</a>
<a onclick="system(event)" >
<div name="n64" class="clearButton">N64</div>
</a>
<a onclick="system(event)" >
<div name="dc" class="clearButton">Dreamcast</div>
</a>
</body>
"""
    def cmd_crosspoint(self,cmd):
        cross = serial.Serial(self.serial_crosspoint,9600,timeout=30,parity=serial.PARITY_NONE,)
        cross.write( bytes(cmd,'ascii',errors='ignore') )

    def cmd_rt4k(self,cmd):
        rt4k = serial.Serial(self.serial_rt4k,115200,timeout=30,parity=serial.PARITY_NONE,)
        rt4k.write( bytes(cmd+"\n",'ascii',errors='ignore') )

    def cmd_dvs510(self,cmd):
        try:
            endpoint=f"http://192.168.0.109/?cmd={cmd}!"
            req =  request.Request(endpoint)
            resp = request.urlopen(req)
        except Exception as e:
            pprint(e)

    def web_in1606(self):
        print("New Request")
        data = self.request.get_json()
        pprint(data)

        # Send command
        try:
            # Post Method is invoked if data != None
            endpoint=f"http://192.168.0.214/api/swis/resources"
            payload = f'[{{"uri":"/av/out/1/input/main","value":"{data['cmd']}"}}]'
            print("payload: "+payload)

            #data=json.dumps(f'[{{["uri":"/av/out/1/input/main","value":"{data['cmd']}"]}}]').encode("utf-8")
            req =  request.Request(endpoint, data=payload.encode("utf-8"))

            # Response
            resp = request.urlopen(req)
        except Exception as e:
            # Web server probably isn't running, fail silently
            return

        return "sure"

    def web_dvs510(self):
        print("New Request")
        data = self.request.get_json()
        pprint(data)

        # Send command
        try:
            # Post Method is invoked if data != None
            endpoint=f"http://192.168.0.109/?cmd={data['cmd']}!"

            #data=json.dumps(f'[{{["uri":"/av/out/1/input/main","value":"{data['cmd']}"]}}]').encode("utf-8")
            req =  request.Request(endpoint)

            # Response
            resp = request.urlopen(req)

        except Exception as e:
            # Web server probably isn't running, fail silently
            pprint(e)
            return

        return "sure"


    def web_crosspoint(self):
        data = self.request.get_json()

        cross = serial.Serial(self.serial_crosspoint,9600,timeout=30,parity=serial.PARITY_NONE,)
        rt4k = serial.Serial(self.serial_rt4k,115200,timeout=30,parity=serial.PARITY_NONE,)
        pprint(data)
        match data['cmd']:
            case "snes":
                # Send command
                cross.write( bytes("1*2!",'ascii',errors='ignore') )
                cross.write( bytes("1*3!",'ascii',errors='ignore') )

            case "n64":
                # Send command
                cross.write( bytes("2*2!",'ascii',errors='ignore') )
                cross.write( bytes("2*3!",'ascii',errors='ignore') )

            case "dc":
                # Send command
                cross.write( bytes("3*2!",'ascii',errors='ignore') )
                cross.write( bytes("3*4!",'ascii',errors='ignore') )
        return "sure"


    def web_system(self):
        data = self.request.get_json()
        pprint(data)
        self.cmd_rt4k(self.config[data['cmd']]["rt4k"])
        self.cmd_dvs510(self.config[data['cmd']]["dvs510"])
        for tie in self.config[data['cmd']]["crosspoint"]:
                self.cmd_crosspoint(tie)


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



async def startWeb(ip,port,serial,split):

    # Internal Modules
    global server
    server = WebInterface(ip,port,serial,split)

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
    parser.add_argument('-s', '--serial', help="Serial port, can also be a name instead of device path", default="/dev/ttyUSB0")
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
    asyncio.run(startWeb(args.ip,args.port,args.serial,args.split))
    sys.exit(0)



if __name__ == "__main__":
    main()

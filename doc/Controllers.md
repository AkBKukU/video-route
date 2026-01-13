# Supported Video Controllers

The video route program features generic support for some devices and specific support for others. How you control your device will depend on how you can interface with it. Devices are defined in the `video_controllers` section of the configuration JSON. Their key is used an identifier in any sources that send commands through them.

### Example
All interfaces have properties that need to be filled in to use.

     "video_controllers":{
        "rt4k":{
            "name":"Retrotink 4K",
            "type":"serial",
            "baud":115200,
            "parity":"N",
            "serial":"FT232R USB UART - FT232R USB UART",
            "cmd_delay":0,
            "line_end":"\n"
        }
    }


*In this case the key `rt4k` will be used to send commands to this device from sources. *

## Universal Properties

- `name`: Human readable name, used for debugging if commands fail  
- `type`: Used to tell the software the kind of device to initialize as
- `cmd_delay`: Delay in seconds after each command before executing next command  
- `cmd_init` : Commands to send initialize device. Can be bypassed with the `-r` parameter

# Generic Interfaces

Devices with generic interfaces like Extron's SiS commands can be used over different types of software interfaces defined below.

All commands for generic interfaces use a command simple list `[1,2,3]` in sources.

## Serial

*Requires `pyserial` python module*

Device examples:

- Retrotink 4K
- Extron Crosspoint RGB 300

Serial devices can be controlled by a local connection over a serial point. This software supports an additional method of identifying USB serial devices by using their device identifiers. Run `video-route.py -S` to see how you can access your serial devices.

### Properties

- `baud`: Baud rate 
- `parity`: Parity ( Use `N`, `E`, or `O`)
- `serial`: Serial port path, device name, or ID and path values to specify how to access serial device.
- `line_end`: Line end to postpend to all commands. Useful if all commands require carriage returns.

### Example

        "crosspoint":{
            "name":"Extron 300 Crosspoint",
            "type":"serial",
            "baud":9600,
            "parity":"N",
            "serial":"USB-Serial Controller",
            "cmd_init":["#ESCZXXX"]
        }


## Telnet

*Requires `telnetlib3` python module*

Device examples:

- Extron IN1606
- Extron DTP Crosspoint 84

Telnet devices use a remove command line interface to accept commands. This software does not maintain a constant connection to this and instead connects, commands, and disconnects as quickly as possible. There are also some considerations that need to be taken into consideration for each telnet device interface. You will most likely want to connect to the device using a generic telnet client first to understand how to controlit.

### Properties

- `ip` : The IP the telnet server on the device can be accessed at
- `port` : The IP the port telnet server is listening on
- `connection_skip` : The number of lines to discard on initial connection to the device before sending commands

### Example

Note in this example doesn't provide a port because it is assumed to be `23` if not provided.

        "in1606":{
            "name":"Extron IN1606",
            "type":"telnet",
            "connection_skip":3,
            "ip":"192.168.0.214",
            "cmd_delay":0.05
        }


## HTTP GET

Device examples:

- Extron DVS510

If your device has a basic HTTP URL API the this method will allow you to use that as an extremely simple method of control.

### Properties

- `ip` : The IP the server on the device can be accessed at. Port may be specified after
- `uri` : The resource path on the server to access the command API at

### Example

        "dvs510":{
            "name":"Extron DVS 510",
            "type":"http_get",
            "ip":"192.168.0.109",
            "uri":"/?cmd="
        }


# Dedicated Interfaces

Dedicated interfaces currently are implemented using device specific modules that have functions for device commands. The functions for the modules are accessed by using **string names** of the functions with parameters specifed in a list.


All commands for generic interfaces use a command function & parameter list `[{"function1_name":["paramter1","parameter2"]},{"function2_name":["paramter1","parameter2"]}]` in sources.

## ATEM

*Requires [`PyATEMMax`](https://pypi.org/project/PyATEMMax/) python module*

Device examples:

- Blackmagic Design ATEM Pro Mini ISO

See [list of module functions](https://clvlabs.github.io/PyATEMMax/docs/methods/set/) for more information on controlling this device type.


### Properties

- `ip` : The IP the Atem device can be accessed at

### Example

        "atem":{
            "name":"Atem Pro Mini ISO",
            "type":"atem",
            "ip":"192.168.0.157"
        }


## OBS

*Requires [`obsws-python`](https://pypi.org/project/obsws-python/1.1.0/) python module*


See [list of module functions](https://github.com/aatikturk/obsws-python/blob/main/obsws_python/reqs.py) for more information on controlling this device type.

Web socket server must be enabled in OBS for this to work.

### Properties

- `ip` : The IP the computer running OBS
- `port` : The IP the port for the web socket server
- `timeout` : Connection timeout delay
- `password` : Password for access control

### Example

        "stream-pc":{
            "name":"Streaming Computer",
            "type":"obs",
            "timeout":3,
            "password":"myawesomepassword",
            "ip":"127.0.0.1",
            "port":"4455"
        }





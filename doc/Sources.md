# Sources

Sources is what this software calls the control buttons in the web interface that send commands to the video controllers. Sources are all defined in the same way but have many different options and can be nested further for more advanced layouts.

## Example
All interfaces have properties that need to be filled in to use.

     "sources":{
        "rt4k":{
            "name":"RT4K Controls",
            "sources":{
                "rt4k-power":{
                    "name":"Power",
                    "color":"#FFF",
                    "background":"#c00",
                    "rt4k":["remote pwr","pwr on"]
                    },
                "rt4k-phase":{
                    "name":"Phase",
                    "rt4k":["remote phase"]
                    },
                "rt4k-gain":{
                    "name":"Gain",
                    "rt4k":["remote gain"]
                    }
                }
            }
        }
    }


### Universal Properties

The `key` for the source is used as an attributte in the web interface to access its commands. Sources also have the following universal properties.

- `name`: Human readable name printed in the front end
- `description`: Longer text box that is printed to the web front end. Will change the display mode of the source to full width even if the text is empty.
- `color` : Sets text color for source in front end (uses CSS color specifiers)
- `background` : Sets text color for source in front end (uses CSS color specifiers)
- `icon` : Looks for a file name matching the provided string in `http/static/icons/`
- `overlay` : Some generic images that can be overlayed over `icon` image or on right of full width sources. Intended to indicate scaling modes. Choose from [crop, full, pixel, wide].


### Source Groups

It is possible to nest sources by putting another `sources` entry inside a source. This will convert it to a group that displays as an HTML `fieldset` with the name as a `legend` if provided. If there is a legend you can click it to hide the group, the `hide` property can be added to the source and set to `true` to have a group start out hidden.
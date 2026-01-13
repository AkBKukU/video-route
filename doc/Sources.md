# Sources

Sources are what this software calls the control buttons in the web interface that send commands to the video controllers. Sources have command sequences assigned to them using the keys from the video controllers. When a source is activated by the front end it sends all commands to the devices they have defined.

Sources are all defined in the same way but have many different options and can be nested further for more advanced layouts. The structure and options sources have are what determine the layout of the front end.

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
- `description`: Longer text box that is printed to the web front end. Will change the display mode of the source to full width.
- `color` : Sets text color for source in front end (uses CSS color specifiers)
- `background` : Sets text color for source in front end (uses CSS color specifiers)
- `icon` : Looks for a file name matching the provided string in `http/static/icons/`. Can also use [stmpe, crop, full, pixel, wide] as generic image options.

## Source Layouts

Depending on what options are added to a source entry, they will be visualized in the layout in three different ways.

### Buttons

Sources are considered "buttons" when they don't have a description. Buttons are kept as small as possible and will be arranged horizontally and wrap down a line to fit on screen. Buttons may have icons and names, but both are not required.

Names will be placed under icons.

### Lists

Sources are considered "lists" when they have a description, even if it is empty. List items will fill the horizontal space of the page.

Names and descriptions are grouped and displayed to the right of an icon, if the page with is narrower than 600px (half the max width for an icon) the text will appear under the icon.


### Source Groups

It is possible to nest sources by putting another `sources` entry inside a source. This will convert it to a group that displays as an HTML `fieldset` with the name as a `legend` if provided. If there is a legend you can click it to hide the group, the `hide` property can be added to the source and set to `true` to have a group start out hidden.

Groups can have an empty `sources` section which is useful if you want to have the text of a description be hidable. The [config-sample.json](../config-sample.json) file has an example of this in the "Extron DTP 84" group. 

Buttons and lists are shown inside groups the same way as before but constrained to the group. Groups themselves behave like lists and fill the horizontal space of the page.

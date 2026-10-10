# `surftrak3.lua`

The [surftrak3.lua](surftrak3.lua) script lets you specify a _desired_ rangefinder target, and it will constantly
update the _current_ rangefinder target as needed, simplifying the process of maintaining a constant distance to the
seafloor.

> Be careful! The sub will move at PILOT_SPEED_DN/UP cm / second to achieve the rangefinder target.
> Even with reasonable settings (PILOT_SPEED_DN = 50 cm/s) I recommend diving under pilot control until you are fairly
> close to the target, then using the script to set the target exactly.

## Installation

Enable Lua scripting in ArduSub:
~~~
SCR_ENABLE 1
~~~

Reboot ArduSub to start scripting.

Set these parameters (modify as desired):
~~~
SCR_USER1 200   # Rangefinder target, in cm
SCR_USER2 10    # Rangefinder target increment / decrement amount, in cm
~~~

The script uses 3 of the 4 script buttons:
* Script button 1 (function 108) sets the rangefinder target to `SCR_USER1`
* Script button 2 (function 109) increments the target by `SCR_USER2`
* Script button 3 (function 110) decrements the target by `SCR_USER2`

Suggested settings for the Xbox controller:
* Map the shift-dpad-right button (`BTN14_SFUNCTION`) to script button 1
* Map the shift-dpad-up button (`BTN11_SFUNCTION`) to script button 2
* Map the shift-dpad-down button (`BTN12_SFUNCTION`) to script button 3

You can do this in the Cockpit UI, or you can modify the parameters directly:
~~~
BTN14_SFUNCTION 108  # shift-dpad-right button sets the rangefinder target
BTN11_SFUNCTION 109  # shift-dpad-up button increments the target
BTN12_SFUNCTION 110  # shift-dpad-down button decrements the target
~~~

Check your settings for PILOT_SPEED_UP and PILOT_SPEED_DN. (If PILOT_SPEED_DN is 0 then PILOT_SPEED_UP is used for both
up and down movement.) These settings work fairly well:
~~~
PILOT_SPEED_DN	50    # Max speed down is 50 cm/s
PILOT_SPEED_UP	50    # Max speed up is 50 cm/s
~~~

Copy `surftrak3.lua` to the `/root/.config/blueos/ardupilot-manager/firmware/scripts` folder
in the blueos-core Docker container on the Raspberry Pi. You can do this using BlueOS:
* Turn on _Pirate mode_
* Start the _File Browser_
* Drill into _configs_, _ardupilot-manager_, _firmware_, _scripts_
* Upload the script to this folder

Reboot ArduSub to load and run the script. You should see "surftrak3.lua loaded" appear in the boot messages.

## Pilot Interface

Press shift-dpad-right to set the rangefinder target to SCR_USER1 (in cm). The sub will ascend or descend to achieve the
target. The vertical speed is controlled by the PILOT_SPEED_UP and PILOT_SPEED_DN parameters.

Press shift-dpad-up to increment the rangefinder target by SCR_USER2.
Press shift-dpad-down to decrement the rangefinder target by SCR_USER2.

Each target change will appear in the message list.

Note that the target is **sticky across mode switches** and is only forgotten when the sub is disarmed. If the pilot uses
the throttle stick to hop over an obstacle while in SURFTRAK mode, the target is automatically re-applied once the stick
is centered. The vehicle will descend back to the target distance so that the pilot can resume the transect.

ArduSub will ignore the new rangefinder target if any of the following are true:
* The sub is not in SURFTRAK mode
* The sub is higher than SURFTRAK_DEPTH
* The new rangefinder target is < RNGFNDx_MIN or > RNGFNDx_MAX

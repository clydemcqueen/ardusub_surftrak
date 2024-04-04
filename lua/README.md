# Surftrak Lua Script

The [surftrak_buttons.lua](surftrak_buttons.lua) script allows you to use the joystick to set the rangefinder target
to a specific value, and to increment or decrement that value.

> This is experimental and subject to change!

> Be careful using this script! The ROV will move at PILOT_SPEED_DN/UP cm / second to achieve the rangefinder target.
> Even with reasonable settings (PILOT_SPEED_DN = 50 cm/s) I recommend diving under pilot control until you are fairly
> close to the target, then using the script to set the target exactly.

## Installation

Enable Lua scripting in ArduSub:
~~~
SRC_ENABLE 1
~~~

Reboot ArduSub to start scripting.

Set these parameters:
~~~
SCR_USER1 200   # Rangefinder target, in cm
SCR_USER2 10    # Rangefinder target increment / decrement amount, in cm

BTN0_SFUNCTION  108   # XBox controller shift-A: set target to SCR_USER1
BTN1_SFUNCTION  109   # XBox controller shift-B: increment target by SCR_USER2
BTN2_SFUNCTION  110   # XBox controller shift-X: decrement target by SCR_USER2
~~~

Check your settings for PILOT_SPEED_UP and PILOT_SPEED_DN. (If PILOT_SPEED_DN is 0 then PILOT_SPEED_UP is used for both
up and down movement.) These settings work fairly well:
~~~
PILOT_SPEED_DN	50    # Max speed down is 50 cm/s
PILOT_SPEED_UP	50    # Max speed up is 50 cm/s
~~~

Copy [surftrak_buttons.lua](surftrak_buttons.lua) to the `/root/.config/blueos/ardupilot-manager/firmware/scripts` folder
in the blueos-core Docker container on the Raspberry Pi. You can do this using BlueOS:
* Turn on _Pirate mode_
* Start the _File Browser_
* Drill into _configs_, _ardupilot-manager_, _firmware_, _scripts_
* Upload the script to this folder

Reboot ArduSub to load and run the script.

## Pilot Interface

Press shift-A to set the rangefinder target to SCR_USER1 (in cm). The sub will ascend or descend to achieve the target.
The vertical speed is controlled by the PILOT_SPEED_UP and PILOT_SPEED_DN parameters.

Press shift-B to increment the rangefinder target by SCR_USER2.
Press shift-X to decrement the rangefinder target by SCR_USER2.

Each target change will appear in the QGC message list.

Everytime you switch modes the target is forgotten.

The script will run several error checks:
* If SCR_USER1 is missing or < 100 cm, then you'll see a message every 10s describing the problem
* If SCR_USER2 is missing or < 1 cm, then you'll see a message every 10s describing the problem
* If the rangefinder is not healthy when you press one of the buttons the button press will be ignored
* If the new rangefinder target is < 80cm it will be set to 80cm

ArduSub will ignore the new rangefinder target if any of the following are true:
* The sub is not in SURFTRAK mode
* The sub is higher than SURFTRAK_DEPTH
* The new rangefinder target is < RNGFNDx_MIN or > RNGFNDx_MAX

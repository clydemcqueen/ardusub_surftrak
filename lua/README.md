# Surftrak Lua Scripts

There are 2 surftrak Lua scripts. Both scripts let you set the rangefinder target to a specific value (e.g., 100cm) and
to increment or decrement the rangefinder target by a specific amount (e.g., 10cm). The 2 scripts differ in how they 
respond to pilot overrides.

The [surftrak_buttons.lua](surftrak_buttons.lua) script will set or adjust the  rangefinder target only when
you press the buttons. If you move the sub up or down using the vertical stick, surftrak will automatically adjust the
rangefinder target to maintain the new altitude. If you want to set the target to 100cm again you can press the button
again.

In some situations you may need to apply a fair amount of yaw or sway thrust to counteract currents, and so you may end
up moving the vertical stick by accident. Or you may be moving over a very dynamic seafloor where you have to move up
and down fairly often. In both cases you may need to pay close attention to the rangefinder target and be ready to
restore it to 100cm as soon as possible.

The [surftrak2.lua](surftrak2.lua) script lets you specify a _desired_ target, and it will constantly
update the _current_ rangefinder target as needed, simplifying the process of maintaining a constant distance to the
seafloor.

> This is experimental and subject to change!

> Be careful! The sub will move at PILOT_SPEED_DN/UP cm / second to achieve the rangefinder target.
> Even with reasonable settings (PILOT_SPEED_DN = 50 cm/s) I recommend diving under pilot control until you are fairly
> close to the target, then using the script to set the target exactly.

## Installation

Enable Lua scripting in ArduSub:
~~~
SRC_ENABLE 1
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

Copy 1 (not both!) of the scripts to the `/root/.config/blueos/ardupilot-manager/firmware/scripts` folder
in the blueos-core Docker container on the Raspberry Pi. You can do this using BlueOS:
* Turn on _Pirate mode_
* Start the _File Browser_
* Drill into _configs_, _ardupilot-manager_, _firmware_, _scripts_
* Upload the script to this folder

Reboot ArduSub to load and run the script. You should see "surftrak2.lua running" appear very early in the boot messages.

## Pilot Interface

Press shift-dpad-right to set the rangefinder target to SCR_USER1 (in cm). The sub will ascend or descend to achieve the
target. The vertical speed is controlled by the PILOT_SPEED_UP and PILOT_SPEED_DN parameters.

Press shift-dpad-up to increment the rangefinder target by SCR_USER2.
Press shift-dpad-down to decrement the rangefinder target by SCR_USER2.

Each target change will appear in the message list.

Every time you switch modes the target is forgotten.

The script will run several error checks:
* If SCR_USER1 is missing or < 50 cm, then you'll see a message every 10s describing the problem
* If SCR_USER2 is missing or < 1 cm, then you'll see a message every 10s describing the problem
* If the rangefinder is not healthy when you press one of the buttons the button press will be silently ignored
* If the new rangefinder target is < 50cm it will be set to 50cm

ArduSub will ignore the new rangefinder target if any of the following are true:
* The sub is not in SURFTRAK mode
* The sub is higher than SURFTRAK_DEPTH
* The new rangefinder target is < RNGFNDx_MIN or > RNGFNDx_MAX

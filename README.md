# Surftrak Flight Mode

We propose a [range hold (SURFTRAK) flight mode for ArduSub](https://github.com/ArduPilot/ardupilot/pull/23435)
inspired by the [surface tracking feature in ArduCopter](https://ardupilot.org/copter/docs/terrain-following-manual-modes.html).

## Operation

The range hold (SURFTRAK) mode is similar to altitude hold (ALT_HOLD), but uses healthy rangefinder readings to
adjust that target depth as the seafloor rises and falls.

Normal operation:
* The pilot flies the sub to the desired altitude above the seafloor and switches to SURFTRAK mode.
* The current depth becomes the depth target, and the current rangefinder reading becomes the rangefinder target.
* The depth target is adjusted using AC_PosControl offsets to maintain the rangefinder target.

Normal operation requires a healthy down-facing rangefinder. A MAVLink rangefinder is healthy if:
* The most recent reading was received within the last 500ms, and
* The most recent signal quality (if present in the message) is above RNGFND_SQ_MIN, and
* The 3 most recent readings were between the min and max specified in RNGFND parameters or DISTANCE_SENSOR messages.

SURFTRAK behaves like ALT_HOLD if the pilot takes control (the throttle stick is not in the deadzone): the sub ascends
or descends until the pilot releases control. The rangefinder target is updated to reflect the change in depth.

The pilot can switch to SURFTRAK mode even if the rangefinder is unhealthy. In this case SURFTRAK starts in a _reset_ state:
there is a depth target, but there is no rangefinder target. When the rangefinder becomes healthy the sub sets
the rangefinder target and starts tracking the seafloor.

There are 2 conditions that will cause SURFTRAK to reset:
* The sub hits the surface (that is, the depth > SURFACE_DEPTH)
* The sub hits the ground (that is, the vertical thrusters are maxed out but the sub is not moving)

In these cases SURFTRAK will set a new rangefinder target when the condition is over and the rangefinder is healthy. 

To avoid hitting the surface and resetting the rangefinder target, SURFTRAK mode will keep the sub below SURFTRAK_DEPTH
by allowing the sub to get closer to the rising seafloor. When the seafloor falls again the sub will follow it down.
The default SURFACE_DEPTH is -10 cm and the default SURFTRAK_DEPTH is -50 cm, so it is unlikely that the sub will hit
the surface while in SURFTRAK mode.

If the rangefinder becomes unhealthy while SURFTRAK mode is active, then SURFTRAK stops adjusting the target depth.
When the rangefinder becomes healthy again then SURFTRAK will resume tracking the seafloor.

There are Lua bindings to support other actions. See the [example script](lua/README.md) for details.

## Pilot Interface

To activate SURFTRAK in mavproxy, enter command "mode 21".

You can associate SURFTRAK with a joystick button in QGroundControl:
* Select Vehicle Setup > Parameters
* Select the BTNx_FUNCTION or BTNx_SFUNCTION parameter for the button you want to map to SURFTRAK
* In the Parameter Editor, select Advanced Settings
* Select Manual Entry
* Type 13 (referring to joystick function 13) in the edit box
* Select Save

You should see the following in QGroundControl:
* SURFTRAK appears as "Unknown" in the mode dropdown menu
* If the rangefinder is unhealthy you will see this info message: **waiting for a rangefinder reading**
* If the depth > SURFTRAK_DEPTH you will see this warning message: **descend below n.nn meters to hold range**
* When the target rangefinder is set or changed you will see this info message: **rangefinder target is n.nn meters**

Proposed changes to QGroundControl (see [code](https://github.com/mavlink/qgroundcontrol/compare/master...clydemcqueen:qgroundcontrol:clyde_surftrak)):
* SURFTRAK appears as "Surftrak" in the mode dropdown menu.
* The current rangefinder target can be displayed in the instrument panel.
* The parameter defaults are updated so it is easier to assign mode_surftrak to joystick buttons.

## Sensor Notes

We have tested SURFTRAK with a Blue Robotics Ping (v1) and a Water Linked DVL A50.
Both use the ArduPilot AP_RangeFinder_MAVLink backend.

Notes on the AP_RangeFinder_MAVLink backend:
* The DISTANCE_SENSOR.covariance, horizontal_fov and vertical_fov fields are ignored. All readings are considered good if they are between min and max.
* The rangefinder max distance is `min(DISTANCE_SENSOR.max_distance, RNGFND1_MAX_CM)`
* Similarly, the rangefinder min distance is `max(DISTANCE_SENSOR.min_distance, RNGFND1_MIN_CM)`
* The default value for RNGFND1_MAX_CM is 700 cm, so if you can't get SURFTRAK to work far away from the seafloor, check this value!
* The DISTANCE_SENSOR.time_boot_ms is ignored, the current time is used instead.

We measured sensor delay for the Ping v1 at ~800ms and for the A50 at ~300ms. A long delay can result in depth
oscillation. You can reduce this oscillation by modifying the PSC_JERK_Z and PILOT_ACCEL_Z. The goal is to get the
[KPv value](https://github.com/ArduPilot/ardupilot/blob/15cea77e98d51a5371c38115ee56eb7a85ab26ff/libraries/AP_Math/control.cpp#L301)
less than 1.0, ideally around 0.8. Here's the math:

~~~
jerk_cm = PSC_JERK_Z * 100
accel_cm = PILOT_ACCEL_Z            # For SURFTRAK mode
accel_cm = WPNAV_ACCEL_Z            # For AUTO and GUIDED modes
KPv = 0.5 * jerk_cm / accel_cm
~~~

For the A50 these settings work fairly well:
~~~
PSC_JERK_Z 8
PILOT_ACCEL_Z 500
WPNAV_ACCEL_Z 500
~~~

## Testing in Simulation

You can run tests using the scripts provided in this repo, including [sitl_runner.py](sitl_runner.py).
The test runs are fully automated and support several features:
* They can run faster than wall-clock time
* You can provide custom terrain, change sensor delay, add dropouts, etc.
* You can test missions (AUTO mode)

### Install

Surftrak has been merged into ArduPilot, so you can test this on the master branch or the Sub-4.5 branch.

Install ArduPilot from https://github.com/ArduPilot/ardupilot in `~/ardupilot`

Install https://github.com/clydemcqueen/ardusub_surftrak in `~/projects/ardusub_surftrak`

### Procedure

Checkout and build ArduPilot:
~~~
cd ~/ardupilot
waf configure --board sitl
waf sub
~~~

The [sitl_runner.py](sitl_runner.py) script does the following:
* starts ArduSub
* loads parameters from [params/sitl.params](params/sitl.params)
* reboots ArduSub
* runs the simulation, injecting rangefinder data using MAVLink
* quits the simulation after a period of time

This example will run a simulation with a sawtooth terrain, 20X faster than wall-clock time, for 150 simulated seconds:
~~~
sitl_runner.py --terrain terrain/sawtooth.csv --speedup 20 --time 150
~~~

The [run_sitl.bash](run_sitl.bash) script automates the log processing. It does the following:
* calls [sitl_runner.py](sitl_runner.py) to run the simulation
* extracts the CTUN table from the dataflash log as a csv file and merges it with the terrain data csv file
* generates a graph using matplotlib and saves it as a PDF file
* moves the simulation products (dataflash log, csv files, graph) to a directory for later review

Finally, the [run_all.bash](run_all.bash) script will run 6 simulations over the 6 different terrain types and save
the results for review:
~~~
export ARDUPILOT_HOME=~/ardupilot
source run_all.bash
~~~

### Results

There are 6 pre-generated terrain files:
* trapezoid: 5m rise, ramp up and down
* sawtooth: 1m rise, jump up, ramp down
* square: a square wave
* zeros: flat
* stress: a series of sharp jumps
* test_signal_quality: includes bad readings and dropouts

Each SITL test results in 4 files:
* ctun.csv: output of `mavlogdump.py --types CTUN --format csv 000000xx.BIN > ctun.csv`
* stamped_terrain.csv: output of `sitl_runner.py`
* merged.csv: output of `merge_logs.py`
* merged.pdf: output of `graph_sitl.py`

Each graph consists of 3 sections:
* altitude readings (in m)
* rangefinder readings (in m)
* climb rates (in cm)

Variables graphed in the altitude section:
* CTUN.DAlt: the target z value the controller is trying to achieve
* CTUN.Alt: the best estimate of the current z value from the EKF
* CTUN.TAlt: the offset target used by AC_PosControl
* Older sub pos: the z value used by the data injector (sitl_runner.py keeps past z values to simulate a delay)
* Older terrain pos: the simulated terrain height at that time

Variables graphed in the rangefinder section:
* CTUN.DSAlt: the target rangefinder value that the controller is trying to achieve
* CTUN.SAlt: the current rangefinder reading
* Injected rangefinder: the rangefinder reading injected by the data injector

Variables graphed in the climb rate section:
* CTUN.DCRt: the target climb rate value that the controller is trying to achieve
* CTUN.CRt: the climb rate that will be sent to the thrusters

## Testing on Hardware

It is still early days! Caveat emptor!

SURFTRAK is on master and the Sub-4.5 branch.

As of 29-Feb-2024 it is currently building on the BETA track,
e.g., see the [navigator beta build](https://firmware.ardupilot.org/Sub/beta/navigator/git-version.txt).


To install:
* Save your parameters so that you can undo the installation
* Install BETA firmware using BlueOS
* [Map SURFTRAK to a button on the joystick](lutris/test_surf.params)
* [Tune for your depth finder, e.g., the A50](lutris/test_KPv.params)
* Optional: install the [SURFTRAK Lua script](lua/README.md) to add additional controls

See the [tracking bug](https://github.com/clydemcqueen/ardusub_surftrak/issues/4) for status of the various components.

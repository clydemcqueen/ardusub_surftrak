# Range Hold Flight Mode

We propose a [range hold (RNG_HOLD) mode for ArduSub](https://github.com/clydemcqueen/ardupilot/tree/clyde_surftrak)
inspired by the [surface tracking feature in ArduCopter](https://ardupilot.org/copter/docs/terrain-following-manual-modes.html).

## Operation

The range hold (RNG_HOLD) mode is similar to altitude hold (ALT_HOLD), but uses healthy rangefinder readings to
adjust that target depth as the seafloor rises and falls.

Normal operation:
* The pilot flies the sub to the desired altitude above the seafloor and switches to RNG_HOLD mode.
* The current depth becomes the depth target, and the current rangefinder reading becomes the rangefinder target.
* The depth target is adjusted using AC_PosControl offsets to maintain the rangefinder target.

Normal operation requires a healthy down-facing rangefinder. A MAVLink rangefinder is healthy if:
* The most recent reading was received within the last 500ms, and
* The most recent signal quality (if present in the message) is above 90, and
* The 3 most recent readings were between the min and max specified in RNGFND parameters or DISTANCE_SENSOR messages.

RNG_HOLD behaves like ALT_HOLD if the pilot takes control (the throttle stick is not in the deadzone): the sub ascends
or descends until the pilot releases control. The rangefinder target is updated to reflect the change in depth.

The pilot can switch to RNG_HOLD mode even if the rangefinder is unhealthy. In this case RNG_HOLD starts in a _reset_ state:
there is a depth target, but there is no rangefinder target. When the rangefinder becomes healthy the sub sets
the rangefinder target and starts tracking the seafloor.

There are 2 conditions that will cause RNG_HOLD to reset:
* The sub hits the surface (that is, the depth > SURFACE_DEPTH)
* The sub hits the ground (that is, the vertical thrusters are maxed out but the sub is not moving)

In these cases RNG_HOLD will set a new rangefinder target when the condition is over and the rangefinder is healthy. 

To avoid hitting the surface and resetting the rangefinder target, RNG_HOLD mode will keep the sub below RNGHOLD_DEPTH
by allowing the sub to get closer to the rising seafloor. When the seafloor falls again the sub will follow it down.
The default SURFACE_DEPTH is -10 cm and the default RNGHOLD_DEPTH is -50 cm.

If the rangefinder becomes unhealthy while RNG_HOLD mode is active, then RNG_HOLD stops adjusting the target depth.
When the rangefinder becomes healthy again then RNG_HOLD will resume tracking the seafloor.

There are Lua bindings to support other actions. See the [example script](lua/README.md) for details.

## Pilot Interface

To activate RNG_HOLD in mavproxy, enter command "mode 21".

You can associate RNG_HOLD with a joystick button in QGroundControl:
* Select Vehicle Setup > Parameters
* Select the BTNx_FUNCTION or BTNx_SFUNCTION parameter for the button you want to map to RNG_HOLD
* In the Parameter Editor, select Advanced Settings
* Select Manual Entry
* Type 13 (referring to joystick function 13) in the edit box
* Select Save

You should see the following in QGroundControl:
* RNG_HOLD appears as "Unknown" in the mode dropdown menu
* If the rangefinder is unhealthy you will see this info message: **waiting for a rangefinder reading**
* If the depth > RNGHOLD_DEPTH you will see this warning message: **descend below n.nn meters to hold range**
* When the target rangefinder is set or changed you will see this info message: **rangefinder target is n.nn meters**

Proposed changes to QGroundControl:
* RNG_HOLD appears as "Range hold" in the mode dropdown menu.
* The current rangefinder target can be displayed in the instrument panel.

## Sensor Notes

We have tested RNG_HOLD with a Blue Robotics Ping (v1) and a Water Linked DVL A50.
Both use the ArduPilot AP_RangeFinder_MAVLink backend.

Notes on the AP_RangeFinder_MAVLink backend:
* The DISTANCE_SENSOR.covariance, horizontal_fov and vertical_fov fields are ignored. All readings are considered good if they are between min and max.
* The DISTANCE_SENSOR.min_distance and max_distance fields override the RNGFND1_MIN_CM and RNGFND1_MAX_CM parameters.
* The DISTANCE_SENSOR.time_boot_ms is ignored, the current time is used instead.

We measured sensor delay for the Ping v1 at ~800ms and for the A50 at ~300ms. A long delay can result in depth
oscillation. You can reduce this oscillation by modifying the PSC_JERK_Z and PILOT_ACCEL_Z. The goal is to get the KPv
value less than 1.0, perhaps around 0.8. Here's the math:

~~~
jerk_cm = PSC_JERK_Z * 100
accel_cm = PILOT_ACCEL_Z            # For RNG_HOLD mode
accel_cm = WPNAV_ACCEL_Z            # For AUTO and GUIDED modes
KPv = 0.5 * jerk_cm / accel_cm
~~~

For the A50 these settings work fairly well:
~~~
PSC_JERK_Z 8
PILOT_ACCEL_Z 500
WPNAV_ACCEL_Z 500
~~~

# Simulations

You can run tests using [ArduPilot SITL](https://ardupilot.org/dev/docs/using-sitl-for-ardupilot-testing.html).
The SITL runs are fully automated and support several features:
* they can run faster than wall-clock time
* you can provide custom terrain, change sensor delay, add dropouts, etc.
* you can test missions (AUTO mode)

## Install

Install ArduPilot from https://github.com/clydemcqueen/ardupilot in `~/ardupilot`

Install https://github.com/clydemcqueen/ardusub_surftrak in `~/projects/ardusub_surftrak`

## Procedure

Checkout and build the `clyde_surftrak` branch of ardupilot:
~~~
cd ~/ardupilot
git checkout clyde_surftrak
waf configure --board sitl
waf sub
~~~

The [sitl_runner.py](sitl_runner.py) script does the following:
* starts ardusub
* loads parameters from [params/sitl.params](params/sitl.params)
* reboots ardusub
* runs the simulation, injecting rangefinder data
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

## Results

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

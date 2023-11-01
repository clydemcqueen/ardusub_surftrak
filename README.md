# Introduction

We propose a [surface (seafloor) tracking feature for ArduSub](https://github.com/clydemcqueen/ardupilot/tree/clyde_surftrak)
inspired by the [surface tracking feature in ArduCopter](https://ardupilot.org/copter/docs/terrain-following-manual-modes.html).
Surface tracking in ArduSub requires a down-facing rangefinder (e.g., the Blue Robotics Ping Sonar) and is activated by
selecting the new RNG_HOLD flight mode.

The [auto altitude control feature](https://discuss.bluerobotics.com/t/altimeter-and-auto-altitude/2039) was proposed previously.
This feature works by feeding rangefinder data into the ArduPilot EKF as the z position, replacing the barometer input.
This feature is not supported by the ArduSub team, but provides roughly the same functionality as surface tracking.

In this document, surface tracking is referred to as _surftrak_ or _RNG_HOLD_ and auto altitude is referred to as _auto_alt_.

# RNG_HOLD Flight Mode

## Behavior

The RNG_HOLD (range hold) mode uses the ALT_HOLD (altitude hold) logic to hold a target depth, but it uses healthy
rangefinder readings to adjust that target depth as the seafloor rises and falls.

Normal operation:
* The pilot flies the sub to the desired height above the seafloor and switches to RNG_HOLD mode.
* The current depth becomes the depth target, and the current rangefinder reading becomes the rangefinder target.
* The depth target is adjusted (using AC_PosControl offsets) to maintain the rangefinder target.

Normal operation requires a healthy down-facing rangefinder. A rangefinder is healthy if:
* The most recent reading was received within the last 500ms, and
* The 3 most recent readings were between the min and max specified in RNGFND parameters or DISTANCE_SENSOR messages (see Sensor Notes)

The pilot can switch to RNG_HOLD mode even if the rangefinder is unhealthy. In this case RNG_HOLD starts in a "reset" state:
there is a depth target, but there is no rangefinder target. When the rangefinder becomes healthy the sub sets
the rangefinder target and starts tracking the seafloor.

There are 3 other conditions that will cause RNG_HOLD to reset:
* The sub hits the surface (that is, the depth > SURFACE_DEPTH)
* The sub hits the seafloor (the vertical thrusters are maxed out but the sub is not moving)
* The pilot takes control (the throttle stick is not in the deadzone)

In these cases RNG_HOLD will set a new rangefinder target when the condition is over and the rangefinder is healthy. 

If the rangefinder becomes unhealthy while RNG_HOLD mode is active then RNG_HOLD stops adjusting the target depth.
The current target depth is still maintained. When the rangefinder becomes healthy again then RNG_HOLD will resume
tracking the seafloor. Note that the rangefinder target is _not_ reset in this case.

In the example diagram below, RNG_HOLD is engaged and following the expected track until the sub reaches the surface.
At the surface the sub stops ascending (the target depth is set 5cm below SURFACE_DEPTH), RNG_HOLD is put in the reset
state, and the next good rangefinder reading becomes the rangefinder target. This may happen several times as the
seafloor rises and the sub bobs a bit just below the surface. Eventually the seafloor falls away and the sub tracks
the seafloor, but now with a lower rangefinder target.

![images/rng_hold.png](images/rng_hold.png)

## Pilot Interface

To activate RNG_HOLD in mavproxy, enter command "mode 21".

To associate RNG_HOLD with a joystick button in QGroundControl:
* Select Vehicle Setup > Parameters
* Select the BTNx_FUNCTION or BTNx_SFUNCTION parameter for the button you want to map to RNG_HOLD
* In the Parameter Editor, select Advanced Settings
* Select Manual Entry
* Type 13 (referring to joystick function 13) in the edit box
* Select Save

You should see the following in QGroundControl:
* RNG_HOLD appears as "Unknown" in the mode dropdown menu
* If you enter RNG_HOLD mode when the rangefinder is unhealthy you will see (and hear) this warning message: **rangefinder is not OK, holding depth**
* When the target rangefinder is set (or re-set) you will see this info message: **rangefinder target is X.XX m**

Possible future pilot interface (requires changes to MAVLink and QGroundControl):
* RNG_HOLD appears as "Range hold" in the mode dropdown menu.
* The current rangefinder target is displayed in the instrument panel.
* The current rangefinder status (healthy, unhealthy) is displayed in the instrument panel.
* There is a joystick function to set the rangefinder target from a parameter, e.g., RNG_HOLD_TARGET1.
This will make it easy to set an exact rangefinder target during survey missions.

## Sensor Notes

We have tested the Blue Robotics Ping sonar sensor connected via MAVLink.
This uses the ArduPilot AP_RangeFinder_MAVLink backend.

Notes on the AP_RangeFinder_MAVLink backend:
* The DISTANCE_SENSOR.covariance, signal_quality, horizontal_fov and vertical_fov fields are ignored. All readings are considered good if they are between min and max.
* The DISTANCE_SENSOR.min_distance and max_distance fields override the RNGFND1_MIN_CM and RNGFND1_MAX_CM parameters.
* The DISTANCE_SENSOR.time_boot_ms is ignored, the current time is used instead.

Notes on the Ping Sonar sensor:
* From the logs there appears to be a 500ms to 800ms delay between ground truth and the DISTANCE_SENSOR message appearing in ArduSub.
* The sensor is rated to read as low as 0.5m, but we've seen it do quite well down to 0.3m. Readings below 0.3m are erratic. The safest min_distance is 50cm.

# Simulations

We ran tests using the [ArduPilot SITL](https://ardupilot.org/dev/docs/using-sitl-for-ardupilot-testing.html)
simulator with 2 physics models:
* SITL using the built-in SIM_Submarine model; this is referred to as _SITL_
* SITL using [Gazebo Garden Sim](https://gazebosim.org/docs/all/getstarted),
the [ardupilot_gazebo plugin](https://github.com/ArduPilot/ardupilot_gazebo) and the
[bluerov2_ignition](https://github.com/clydemcqueen/bluerov2_ignition) vehicle model;
this is referred to as _Gazebo_

The SITL setup is simpler to install and uses known terrain data so the experiments can be repeated easily.

The SITL setup uses MAVLink GLOBAL_POSITION_INT messages to generate rangefinder values from the terrain data.
This setup introduces some lag.

The SITL setup behaved poorly in tests of auto_alt: the z value was much greater than 0, indicating that the sub 
was floating in the air. 

The Gazebo setup provides a much richer physics model and can be used to run many more
experiments. It works with both surftrak and auto_alt. The terrain data is generated on-the-fly by moving the sub
through the simulated world, so each experiment is unique.

## Install

Install ArduPilot from https://github.com/clydemcqueen/ardupilot in `~/ardupilot`

Install https://github.com/clydemcqueen/ardusub_surftrak in `~/projects/ardusub_surftrak`

Install https://github.com/clydemcqueen/bluerov2_ignition in `~/colcon_ws/src/bluerov2_ignition` and checkout the `ping_sonar` branch

Install https://github.com/ArduPilot/ardupilot_gazebo in `~/simulation/ardupilot_gazebo`

Install Gazebo Garden

Set up some paths:
~~~
# Add ardupilot autotest to the PATH
export PATH=$HOME/ardupilot/Tools/autotest:$PATH

# Add ardupilot_gazebo plugin
export GZ_SIM_SYSTEM_PLUGIN_PATH=$HOME/ardupilot_gazebo/build:$GZ_SIM_SYSTEM_PLUGIN_PATH

# Optional: add ardupilot_gazebo models and worlds
export GZ_SIM_RESOURCE_PATH=$HOME/simulation/ardupilot_gazebo/models:$HOME/simulation/ardupilot_gazebo/worlds:$GZ_SIM_RESOURCE_PATH

# Add bluerov2_ignition models and worlds
export GZ_SIM_RESOURCE_PATH=$HOME/colcon_ws/src/bluerov2_ignition/models:$HOME/colcon_ws/src/bluerov2_ignition/worlds:$GZ_SIM_RESOURCE_PATH
~~~

## Procedure

### SITL (SIM_Submarine)

The SITL runs are fully automated and can run faster than wall-clock time.

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
the results:
~~~
run_all.bash
~~~

### Gazebo Sim

The Gazebo Sim simulations are not automated.

For surftrak, use the `clyde_surftrak` branch in ardupilot. For auto_alt use the `master` branch.

For surftrak use RNG_HOLD mode, for auto_alt use ALT_HOLD.

Launch ArduSub using the standard `sim_vehicle.py` script.
Add the `-w` option to wipe the EEPROM and load default parameters:
~~~
sim_vehicle.py -w -L RATBeach -v ArduSub -w
~~~

Set up the `ardupilot_gazebo` rangefinder in mavproxy:

~~~
param set RNGFND1_TYPE 100        # Type = SITL
param set RNGFND1_FUNCTION 0      # Function = LINEAR
param set RNGFND1_MAX_CM 5000     # Ping max distance is 50m
param set RNGFND1_MIN_CM 50       # Ping min distance is 0.5m
param set RNGFND1_ORIENT 25       # Down
param set RNGFND1_POS_X -0.18
param set RNGFND1_POS_Y 0.0
param set RNGFND1_POS_Z -0.095
~~~

For auto_alt use this param:
~~~
param set EK3_SRC1_POSZ 2       # EK3 position.z source is rangefinder
~~~

Quit ArduSub.

Launch ArduSub again, this time with the `--model=JSON` option.
ArduSub will start and wait for an external physics engine:
~~~
sim_vehicle.py -L RATBeach -v ArduSub --out=udpout:localhost:14551 --model=JSON
~~~

Launch Gazebo Sim with the `br2_ping` model:
~~~
gz sim -v 3 -r sensor.world
~~~

This will connect ArduSub to Gazebo Sim through the `ardupilot_gazebo` plugin so that they are in lock-step.

Use the joystick to run around the simulated world, and watch the sub move up and down over the terrain.

Quit ArduSub and Gazebo Sim.

Save the log and generate a graph:
~~~
# Destination:
export LOG_DIR=~/projects/ardusub_surftrak/results/gazebo/surftrak

# This should be the most recent dataflash log:
export BIN_FILE=~/ardupilot/results/00000068.BIN

# Process the data:
process_gz.bash
~~~

## Results and Discussion

The CTUN (Control TUNing) messages are written by ArduSub at 10Hz using the latest values from the controllers.

In live experiments, the readings from the Ping 1 sonar sensor were delayed ~0.8s when the sub was ~4m off the seafloor.
This could be due to the speed of sound in water, the sensor firmware, and delays caused by data pipeline.
This can cause large (> 1m) oscillations as the sub attempts to hold depth using the rangefinder. A PID controller was
added to address this problem.

### Files

The results are in the [results](results) directory:
* SITL paths are of the form `results/sitl/version/terrain/file`
* Gazebo paths are of the form `results/gazebo/algorithm/file`

There are 6 SITL terrain files:
* trapezoid: 4m rise, ramp up and down
* sawtooth: 4m rise, jump up, ramp down
* square: a square wave
* zeros: flat
* stress: a series of sharp jumps
* test_signal_quality: includes bad readings and dropouts

Each SITL test results in 4 files:
* ctun.csv: output of `mavlogdump.py --types CTUN --format csv 000000xx.BIN > ctun.csv`
* stamped_terrain.csv: output of `sitl_runner.py`
* merged.csv: output of `merge_logs.py`
* merged.pdf: output of `graph_sitl.py`

Each Gazebo test results in 2 files:
* ctun.csv: output of `mavlogdump.py --types CTUN --format csv 000000xx.BIN > ctun.csv`
* ctun.pdf: output of `graph_gz.py`

### surftrak in SITL (trapezoid)

The [trapezoid terrain graph](results/sitl/surftrak/trapezoid/merged.pdf) shows a rise of 4m at a rate of 0.25m/s,
a plateau, then a fall of 4m at the same rate. There are 3 sections:
* altitude readings (in m)
* rangefinder readings (in m)
* climb rates (in cm)

Variables graphed in the altitude section:
* CTUN target z: the target z value the controller is trying to achieve
* CTUN EKF z: the best estimate of the current z value from the EKF
* CTUN barometer z: just the barometer data (the noise is simulated)
* Injection-time z: the z value used by the data injector (sitl_runner.py keeps past z values to simulate a delay)
* Terrain z: the simulated terrain height

Variables graphed in the rangefinder section:
* CTUN target rangefinder: the target rangefinder value that the controller is trying to achieve
* CTUN rangefinder: the current rangefinder reading (the noise is simulated)
* Injected rangefinder: the rangefinder reading injected by the data injector

Variables graphed in the climb rate section:
* CTUN target climb rate: the target climb rate value that the controller is trying to achieve
* CTUN climb rate: the climb rate that will be sent to the thrusters

The rangefinder reading delay is 0.8s. RNGFND_PID* coefficients were tuned using the
[Ziegler–Nichols "no overshoot" method](https://en.wikipedia.org/wiki/Ziegler%E2%80%93Nichols_method):
* Ku = 0.6
* Tu = 7.5
* RNGFND_PID_P = 0.12
* RNGFND_PID_I = 0.03
* RNGFND_PID_D = 0.3

In the altitude section you can see the controller responding to the rangefinder readings with some damping.
There is no overshoot.

In the rangefinder section you can see that the rangefinder readings lag as the sub is moving up and down the ramps.

In climb rate section you can see consistent target climb rates. These will result in moderate thruster efforts.

### surftrak in SITL (sawtooth)

The [sawtooth terrain graph](results/sitl/surftrak/sawtooth/merged.pdf) shows a sharp jump up 4m,
a plateau, and a fall of 4m at 0.25m/s.

The sub climbs quickly (1m/s) but it still takes 4s to reach the rangefinder target.
There is a no overshoot and the response is quite stable.

Reading delay and RNGFND_PID* parameters are the same as the trapezoid case.

### surftrak in Gazebo

The [surftrak Gazebo graph](results/gazebo/surftrak/ctun.pdf) shows a very different simulation environment.
All data is from the CTUN messages. The terrain height is not shown.

The controller does a pretty good job keeping the rangefinder readings in a small band.

_TODO re-run with the PID controller_

### auto_alt in Gazebo

The [auto_alt Gazebo graph](results/gazebo/auto_alt/ctun.pdf) shows a radically different algorithm.
This algorithm works by injecting the rangefinder data into the EKF, replacing the barometer data.
The ALT_HOLD controller has not changed: it still seeks to maintain a constant altitude using the EKF z, but
the EKF is strongly influenced by the rangefinder reading, so this mostly has the same effect of trying 
to hit the rangefinder target.

The most significant difference between the surftrak and auto_alt algorithms is the variance in the rangefinder
section.

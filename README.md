# Introduction

We propose a [surface (seafloor) tracking feature for ArduSub](https://github.com/clydemcqueen/ardupilot/tree/clyde_surftrak)
inspired by the [surface tracking feature in ArduCopter](https://ardupilot.org/copter/docs/terrain-following-manual-modes.html).
Surface tracking in ArduSub requires a down-facing rangefinder (e.g., the Blue Robotics Ping Sonar) and can be enabled
in ALT_HOLD mode to allow the vehicle to maintain a constant altitude above the terrain.

The [auto altitude control feature](https://discuss.bluerobotics.com/t/altimeter-and-auto-altitude/2039) was proposed previously.
This feature works by feeding rangefinder data into the ArduPilot EKF as the z position, replacing the barometer input.
This feature is not supported by the ArduSub team, but provides roughly the same functionality as surface tracking.

In this document, surface tracking is referred to as _surftrak_ and auto altitude is referred to as _auto_alt_.

The repository describes procedures to test surftrak and auto_alt in simulation, as well as the results of those tests.

We ran tests using the [ArduPilot SITL](https://ardupilot.org/dev/docs/using-sitl-for-ardupilot-testing.html)
simulator with 2 physics models:
* SITL using the built-in SIM_Submarine model; this is referred to as _SITL_
* SITL using [Gazebo Garden Sim](https://gazebosim.org/docs/all/getstarted),
the [ardupilot_gazebo plugin](https://github.com/ArduPilot/ardupilot_gazebo) and the
[bluerov2_ignition](https://github.com/clydemcqueen/bluerov2_ignition) vehicle model;
this is referred to as _Gazebo_

The SITL setup is simpler to install and uses known terrain data so the experiments can be repeated easily.

The SITL setup uses MAVLink and LOCAL_POSITION_NED messages to generate rangefinder values from the terrain data.
This setup introduces lag, which adds oscillations.

> TODO explore methods to minimize or eliminate this lag

The SITL setup behaved poorly in tests of auto_alt: the z value was much greater than 0, indicating that the sub 
was floating in the air. 

> TODO investigate further. Is there a way do test this using SIM_Submarine? Is this a bug in SIM_Submarine?

The Gazebo setup provides a much richer physics model and can be used to run many more
experiments. It works with both surftrak and auto_alt. The terrain data is generated on-the-fly by moving the sub
through the simulated world, so each experiment is unique.

> TODO build a Gazebo plugin to inject known terrain data

# Procedure

## Install

> TODO create a Dockerfile

Install ArduPilot from https://github.com/clydemcqueen/ardupilot in `~/ardupilot`

Install https://github.com/clydemcqueen/ardusub_surftrak in `~/projects/ardusub_surftrak`

Install https://github.com/clydemcqueen/bluerov2_ignition in `~/colcon_ws/src/bluerov2_ignition` and check out the `ping_sonar` branch

Install QGroundControl

Install Gazebo Garden

Set up some paths:
~~~
# Add ardusub_surftrak
export PATH=$HOME/projects/ardusub_surftrak:$PATH

# Add ardupilot autotest to the PATH
export PATH=$HOME/ardupilot/Tools/autotest:$PATH

# Add ardupilot_gazebo plugin
export GZ_SIM_SYSTEM_PLUGIN_PATH=$HOME/ardupilot_gazebo/build:$GZ_SIM_SYSTEM_PLUGIN_PATH

# Optional: add ardupilot_gazebo models and worlds
export GZ_SIM_RESOURCE_PATH=$HOME/ardupilot_gazebo/models:$HOME/ardupilot_gazebo/worlds:$GZ_SIM_RESOURCE_PATH

# Add bluerov2_ignition models and worlds
export GZ_SIM_RESOURCE_PATH=$HOME/colcon_ws/src/bluerov2_ignition/models:$HOME/colcon_ws/src/bluerov2_ignition/worlds:$GZ_SIM_RESOURCE_PATH
~~~

Generate the terrain data before starting:
~~~
cd ~/projects/ardusub_surftrak
mkdir terrain
gen_terrain.py
~~~

Launch QGroundControl and leave it running during the experiements. QGroundControl serves a few purposes:
* It sends MAV_DATA_STREAM messages to ArduSub activating various data streams. In particular,
the rangefinder data injector [sub.py](sub.py) needs LOCAL_POSITION_NED messages to function.
* It will allow you to use a wider variety of joysticks for control.
* It makes it easy to see the state of the sub.

## Run the surftrak algorithm in SITL

Checkout the `clyde_surftrak` branch of ardupilot:
~~~
cd ~/ardupilot
git checkout clyde_surftrak
~~~

Launch SITL. Add the `-w` option to wipe the EEPROM and load default parameters:
~~~
sim_vehicle.py -w -L 'seattle aquarium' -v ArduSub
~~~

> TODO load EK2 params to match supported ArduSub firmware

Configure the autopilot to use a MAVLink rangefinder backend:
~~~
param set RNGFND1_TYPE 10       # Type = MAVLink
param set RNGFND1_SCALING 10    # Send scaled data
param set RNGFND1_MAX_CM 5000   # Max distance is 50m
param set RNGFND1_MIN_CM 20     # Min distance is 0.5m
param set RNGFND1_POS_X -0.18
param set RNGFND1_POS_Y 0.0
param set RNGFND1_POS_Z -0.095
param set SIM_SONAR_SCALE 10    # Unscale
~~~

Turn on surftrak mode:
~~~
param set SURFTRAK_MODE 1
~~~

Quit ArduSub.

Launch SITL again, this time drop the `-w` option to avoiding wiping the EEPROM:
~~~
sim_vehicle.py -L 'seattle aquarium' -v ArduSub
~~~

Get into position by arming and diving to -10m:
* arm
* dive to -10m
* stay in MANUAL mode

Start rangefinder data injection:
~~~
cd ~/projects/ardusub_surftrak
python3 sub.py terrain/trapezoid.csv
~~~

You should see rangefinder data being injected:
~~~
csv file: terrain/trapezoid.csv
Waiting for LOCAL_POSITION_NED msg on udpin:localhost:14551...
timestamp 1678220000.4566069, terrain_z -20.0, sub_z -7.645134449005127, rf 12.354865550994873
~~~

Switch to ALT_HOLD mode. You should see output like this in mavproxy showing that surftrak is running:
~~~
AP: rangefinder target is 9.83401 m
~~~

The rangefinder data will start to change, and the sub should move up and down in response.
Run for a while, then quit ArduSub.

Save the logs:
~~~
# Destination:
export LOG_DIR=~/projects/ardusub_surftrak/logs/sitl/surftrak/trapezoid

# This should be the most recent dataflash log:
export BIN_FILE=~/ardupilot/logs/00000068.BIN

# Process the data:
mkdir -p $LOG_DIR
mv stamped_terrain.csv $LOG_DIR
mavlogdump.py --types CTUN --format csv $BIN_FILE > $LOG_DIR/ctun.csv
cd $LOG_DIR
merge_logs.py
~~~

Repeat as necessary for other terrain inputs.

## Run in Gazebo Sim

Run the same basic procedure as above, but with the following changes.

For surftrak, use the `clyde_surftrak` branch in ardupilot. For auto_alt use the `master` branch.

Wipe the EEPROM with `-w` and set up the parameters again.

Set up the `ardupilot_gazebo` rangefinder:
~~~
param set RNGFND1_TYPE 100        # Type = SITL
param set RNGFND1_FUNCTION 0      # Function = LINEAR
param set RNGFND1_MIN_CM 20       # Min distance is 0.5m
param set RNGFND1_MAX_CM 5000     # Max distance is 50m
param set RNGFND1_ORIENT 25       # Down
param set RNGFND1_POS_X -0.18
param set RNGFND1_POS_Y 0.0
param set RNGFND1_POS_Z -0.095
~~~

For surftrak use this param:
~~~
param set SURFTRAK_MODE 1
~~~

For auto_alt use this param:
~~~
param set EK3_SRC1_POSZ 2       # EK3 position.z source is rangefinder
~~~

Launch the `br2_ping` model in Gazebo:
~~~
gz sim -v 3 -r sensor.world
~~~

Launch SITL with the `--model=JSON option`:
~~~
sim_vehicle.py -L RATBeach -v ArduSub --model=JSON
~~~

This will connect SITL to Gazebo Sim through the ardupilot_gazebo plugin so that they are in lock-step.

Use the joystick to run around the simulated world, and watch the sub move up and down over the terrain.

Quit ArduSub.

Save the log:
~~~
# Destination:
export LOG_DIR=~/projects/ardusub_surftrak/logs/gazebo/surftrak

# This should be the most recent dataflash log:
export BIN_FILE=~/ardupilot/logs/00000068.BIN

# Process the data:
mkdir -p $LOG_DIR
mavlogdump.py --types CTUN --format csv $BIN_FILE > $LOG_DIR/ctun.csv
cd $LOG_DIR
~~~

# Results

## Files

The results are in the [logs](logs) directory:
* SITL paths are of the form `logs/sitl/algorithm/terrain/file`
* Gazebo paths are of the form `logs/gazebo/algorithm/file`

You can generate graphs from log files:
~~~
cd ~/projects/ardusub_surftrak
graph_all.py
~~~

There are 2 SITL terrain files:
* trapezoid: 4m rise, ramp up and down
* sawtooth: 4m rise, jump up, ramp down

Each SITL test results in 4 files:
* ctun.csv: output of `mavlogdump.py --types CTUN --format csv 000000xx.BIN > ctun.csv`
* stamped_terrain.csv: output of `sub.py`
* merged.csv: output of `merge_logs.py`
* merged.pdf: output of `graph_all.py`

Each Gazebo test results in 2 files:
* ctun.csv: output of `mavlogdump.py --types CTUN --format csv 000000xx.BIN > ctun.csv`
* ctun.pdf: output of `graph_all.py`

## Discussion

The CTUN (Control TUNing) messages are written by ArduSub at 10Hz using the latest values from the controllers.
As such, they are the best possible data.

The stamped_terrain.csv data is generated by the rangefinder data injector [sub.py](sub.py), which is also running at 10Hz.
However, the data injector needs to know the current position of the sub to calculate and inject an appropriate
rangefinder reading. The position information is coming from LOCAL_POSITION_NED MAVLink messages which are only sent
at 4Hz so the data isn't always up to date. This lag introduces oscillations.
This is an artifact of the way we inject rangefinder data in SITL. It is not present in the Gazebo simulations.

### surftrak in SITL (trapezoid)

The [trapezoid terrain graph](logs/sitl/surftrak/trapezoid/merged.pdf) shows a rise of 4m at a rate of 0.25m/s,
a plateau, then a fall of 4m at the same rate. There are 3 sections:
* altitude readings (in m)
* rangefinder readings (in m)
* climb rates (in cm)

Variables graphed in the altitude section:
* CTUN target z: the target z value the controller is trying to achieve
* CTUN EKF z: the best estimate of the current z value from the EKF
* CTUN barometer z: just the barometer data (the noise is simulated)
* Injection-time z: the z value used by the data injector
* Terrain z: the simulated terrain height

> TODO is GPS data fused as well? If so, disable the GPS inputs

Variables graphed in the rangefinder section:
* CTUN target rangefinder: the target rangefinder value that the controller is trying to achieve
* CTUN rangefinder: the current rangefinder reading (the noise is simulated)
* Injected rangefinder: the rangefinder reading injected by the data injector

Variables graphed in the climb rate section:
* CTUN target climb rate: the target climb rate value that the controller is trying to achieve
* CTUN climb rate: the climb rate that will be sent to the thrusters

In the altitude section you can see the controller responding quickly to the rangefinder readings.

In the rangefinder section, you can see that the rangefinder readings stay in a fairly small band, indicating that
the controller is doing a reasonable job keeping the sub at a fixed distance above the terrain.

> TODO injected rf appears to lag the CTUN rf, which seems wrong. Investigate

### surftrak in SITL (sawtooth)

The [sawtooth terrain graph](logs/sitl/surftrak/sawtooth/merged.pdf) shows a sharp jump up 4m,
a plateau, and a fall of 4m at 0.25m/s. There are some significant changes from the trapezoid case:
* the sub climbs quickly, but the climb rate is clipped by the controller. The max climb rate appears to be 1m/s.
* there is significant overshoot. This is probably made worse by the data delay.

### surftrak in Gazebo

The [surftrak Gazebo graph](logs/gazebo/surftrak/ctun.pdf) shows a very different simulation environment.
All data is from the CTUN messages. The terrain height is not shown.

The controller does a pretty good job keeping the rangefinder readings in a small band.

### auto_alt in Gazebo

The [auto_alt Gazebo graph](logs/gazebo/auto_alt/ctun.pdf) shows a radically different algorithm.
This algorithm works by injecting the rangefinder data into the EKF, replacing the barometer data.
The ALT_HOLD controller has not changed: it still seeks to maintain a constant altitude using the EKF z, but
the EKF is strongly influenced by the rangefinder reading, so this mostly has the same effect of trying 
to achieve a target rangefinder reading.

The most significant difference between the surftrak and auto_alt algorithms is the variance in the rangefinder
section. More investigation is required.

> TODO it isn't obvious from the graphs if the terrain changes are similar; log and merge the terrain height

> TODO how does the IMU influence the EKF in this case? What about GPS?

# Future Work

* address the various TODOs
* improve surftrak performance by adjusting the various parameters
* run the surftrak controller on a live sub, and analyze the logs
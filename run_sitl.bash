#!/bin/bash

# Run sitl_runner.py and graph the results

if [ $# -lt 9 ]; then
  echo "Usage: run_sitl.bash <version> <terrain> <speedup> <duration> <depth> <delay> <mission> <mode> <params>"
  echo "Example: run_sitl.bash surftrak trapezoid 20.0 300 -10 0.3 fr3.txt 21 sitl.params"
  if [[ ${BASH_SOURCE[0]} != ${0} ]]; then
    # If we exit it will close the terminal, return instead
    return 0
  fi
  exit 1
fi

# ARDUPILOT_HOME must be set
if [[ -z "$ARDUPILOT_HOME" ]]; then
  echo "Error: ARDUPILOT_HOME is not set"
  if [[ ${BASH_SOURCE[0]} != ${0} ]]; then
    # If we exit it will close the terminal, return instead
    return 0
  fi
  exit 1
fi

VERSION=$1
TERRAIN=$2
SPEEDUP=$3
DURATION=$4
DEPTH=$5
DELAY=$6
MISSION=$7
MODE=$8
PARAMS=$9

echo "============================================================================================================"
echo "Run simulation version=$VERSION, terrain=$TERRAIN, speedup=$SPEEDUP, duration=$DURATION, depth=$DEPTH, delay=$DELAY, mission=$MISSION, mode=$MODE, params=$PARAMS"
echo "============================================================================================================"

# Make it easy to find the most recent dataflash log
rm logs/*.BIN
rm logs/LASTLOG.TXT

# Run the simulation
python sitl_runner.py --terrain terrain/$TERRAIN.csv --speedup $SPEEDUP --time $DURATION --depth $DEPTH --delay $DELAY --mission mission/$MISSION --mode $MODE --params params/$PARAMS

# Graph results
export LOG_DIR=results/sitl/$VERSION/$TERRAIN
export BIN_FILE=00000001.BIN
source process_sitl.bash

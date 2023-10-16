#!/bin/bash

# Run sitl_runner.py and graph the results

# Usage:
# run_sitl.bash <version> <terrain> <speedup> <duration>
# run_sitl.bash surftrak trapezoid 20.0 300

VERSION=$1
TERRAIN=$2
SPEEDUP=$3
DURATION=$4

echo "========================================================================================"
echo "Run simulation version=$VERSION, terrain=$TERRAIN, speedup=$SPEEDUP, duration=$DURATION"
echo "========================================================================================"

# Make it easy to find the most recent dataflash log
rm logs/*.BIN
rm logs/LASTLOG.TXT

# Run the simulation
python sitl_runner.py --terrain terrain/$TERRAIN.csv --speedup $SPEEDUP --time $DURATION

# Graph results
LOG_DIR=results/sitl/$VERSION/$TERRAIN
BIN_FILE=logs/00000001.BIN
source process_sitl.bash

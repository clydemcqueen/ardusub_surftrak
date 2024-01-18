#!/bin/bash

# Current working directory must be ardusub_surftrak folder
# Caller must set ARDUPILOT_HOME, BIN_FILE and LOG_DIR, e.g.,
#   export ARDUPILOT_HOME=~/ardupilot
#   export BIN_FILE=00000028.BIN
#   export LOG_DIR=results/sitl/surftrak/trapezoid

mkdir -p $LOG_DIR

cp logs/$BIN_FILE $LOG_DIR

mavlogdump.py --types CTUN --format csv $LOG_DIR/$BIN_FILE > $LOG_DIR/ctun.csv
mv stamped_terrain.csv $LOG_DIR
python merge_logs.py
python graph_sitl.py

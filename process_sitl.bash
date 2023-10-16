#!/bin/bash

# Caller must set BIN_FILE and LOG_DIR, e.g.,
# export BIN_FILE=~/ardupilot/results/00000028.BIN
# export LOG_DIR=~/projects/ardusub_surftrak/results/sitl/surftrak/trapezoid

mkdir -p $LOG_DIR
mavlogdump.py --types CTUN --format csv $BIN_FILE > $LOG_DIR/ctun.csv
mv stamped_terrain.csv $LOG_DIR
merge_logs.py
graph_sitl.py

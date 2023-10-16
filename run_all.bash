#!/bin/bash

# Run all of the sitl simulations

run_sitl.bash surftrak zeros 20.0 200
run_sitl.bash surftrak trapezoid 20.0 200
run_sitl.bash surftrak sawtooth 20.0 200
run_sitl.bash surftrak square 20.0 200
run_sitl.bash surftrak stress 20.0 200
run_sitl.bash surftrak test_signal_quality 20.0 200

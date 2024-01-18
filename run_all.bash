#!/bin/bash

# Run all of the sitl simulations

source run_sitl.bash surftrak zeros 20.0 200 -10 0.3 fr10.txt 21 sitl.params
source run_sitl.bash surftrak trapezoid 20.0 200 -10 0.3 fr10.txt 21 sitl.params
source run_sitl.bash surftrak sawtooth 20.0 200 -10 0.3 fr10.txt 21 sitl.params
source run_sitl.bash surftrak square 20.0 200 -10 0.3 fr10.txt 21 sitl.params
source run_sitl.bash surftrak stress 20.0 200 -10 0.3 fr10.txt 21 sitl.params
source run_sitl.bash surftrak test_signal_quality 20.0 200 -10 0.3 fr10.txt 21 sitl.params

open results/sitl/surftrak/zeros/merged.pdf
open results/sitl/surftrak/trapezoid/merged.pdf
open results/sitl/surftrak/sawtooth/merged.pdf
open results/sitl/surftrak/square/merged.pdf
open results/sitl/surftrak/stress/merged.pdf
open results/sitl/surftrak/test_signal_quality/merged.pdf

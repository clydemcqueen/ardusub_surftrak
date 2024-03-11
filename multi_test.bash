#!/bin/bash

source run_sitl.bash mode0 trapezoid 20.0 200 -10 0.3 fr10.txt 21 mode0.params
source run_sitl.bash mode1 trapezoid 20.0 200 -10 0.3 fr10.txt 21 mode1.params
source run_sitl.bash mode2 trapezoid 20.0 200 -10 0.3 fr10.txt 21 mode2.params
source run_sitl.bash mode3 trapezoid 20.0 200 -10 0.3 fr10.txt 21 mode3.params

open results/sitl/mode0/trapezoid/merged.pdf
open results/sitl/mode1/trapezoid/merged.pdf
open results/sitl/mode2/trapezoid/merged.pdf
open results/sitl/mode3/trapezoid/merged.pdf

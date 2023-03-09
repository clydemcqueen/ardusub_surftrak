#!/usr/bin/env python3

"""
Generate csv files with terrain readings
"""

import csv

# Interval between messages, in seconds
# Note: 0.5 will trigger the timeout in ArduSub.
INTERVAL = 0.1

# Nominal seafloor depth
SEAFLOOR_Z = -20.0


# csv files are saved in a directory which is not checked in
def csv_path(prefix):
    return 'terrain/' + prefix + '.csv'


def write_flat_segment(writer, adj: float, t: float):
    for i in range(int(t / INTERVAL)):
        writer.writerow([SEAFLOOR_Z + adj])


def write_ramp_segment(writer, start: float, stop: float, rate: float):
    step = rate * INTERVAL
    num = int((stop - start) / step)
    for i in range(num):
        adj = round(start + i * step, 2)
        writer.writerow([SEAFLOOR_Z + adj])


def gen_zeros():
    # Open for writing. Do not translate newlines.
    with open(csv_path('zeros'), mode='w', newline='') as csvfile:
        datawriter = csv.writer(csvfile, delimiter=',', quotechar='|')

        # Write the interval
        datawriter.writerow([INTERVAL])

        # Write some zeros
        write_flat_segment(datawriter, 0.0, 10.0)


def gen_trapezoid(tallest_bump: float, rate: float, t=10.0):
    # Open for writing. Do not translate newlines.
    with open(csv_path('trapezoid'), mode='w', newline='') as csvfile:
        datawriter = csv.writer(csvfile, delimiter=',', quotechar='|')

        # Write the interval
        datawriter.writerow([INTERVAL])

        # Write a trapezoid
        write_flat_segment(datawriter, 0.0, t)
        write_ramp_segment(datawriter, 0.0, tallest_bump, rate)
        write_flat_segment(datawriter, tallest_bump, t)
        write_ramp_segment(datawriter, tallest_bump, 0.0, -rate)


def gen_sawtooth(tallest_bump: float, rate: float, t=10.0):
    # Open for writing. Do not translate newlines.
    with open(csv_path('sawtooth'), mode='w', newline='') as csvfile:
        datawriter = csv.writer(csvfile, delimiter=',', quotechar='|')

        # Write the interval
        datawriter.writerow([INTERVAL])

        # Write a sawtooth
        write_flat_segment(datawriter, 0.0, t)
        write_flat_segment(datawriter, tallest_bump, t)
        write_ramp_segment(datawriter, tallest_bump, 0.0, -rate)


def gen_square(tallest_bump: float, t=10.0):
    # Open for writing. Do not translate newlines.
    with open(csv_path('square'), mode='w', newline='') as csvfile:
        datawriter = csv.writer(csvfile, delimiter=',', quotechar='|')

        # Write the interval
        datawriter.writerow([INTERVAL])

        # Write a square wave
        write_flat_segment(datawriter, 0.0, t)
        write_flat_segment(datawriter, tallest_bump, t)


def main():
    tallest_bump = 4.0
    rate = 0.25  # m / sec

    gen_zeros()
    gen_trapezoid(tallest_bump, rate)
    gen_sawtooth(tallest_bump, rate)
    gen_square(tallest_bump)


if __name__ == '__main__':
    main()

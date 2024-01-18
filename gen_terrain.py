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

# Positive terrain values cause special behavior
DROPOUT = 1.0               # Do not send message
LOW_SIGNAL_QUALITY = 2.0    # Send signal_quality = 10


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


def write_dropouts(writer, t: float):
    for i in range(int(t / INTERVAL)):
        writer.writerow([DROPOUT])


def write_low_signal_quality(writer, t: float):
    for i in range(int(t / INTERVAL)):
        writer.writerow([LOW_SIGNAL_QUALITY])


def gen_zeros():
    # Open for writing. Do not translate newlines.
    with open(csv_path('zeros'), mode='w', newline='') as csvfile:
        datawriter = csv.writer(csvfile, delimiter=',', quotechar='|', lineterminator='\n')

        # Write the interval
        datawriter.writerow([INTERVAL])

        # Write some zeros
        write_flat_segment(datawriter, 0.0, 10.0)


def gen_trapezoid(tallest_bump: float, rate: float, t=10.0):
    # Open for writing. Do not translate newlines.
    with open(csv_path('trapezoid'), mode='w', newline='') as csvfile:
        datawriter = csv.writer(csvfile, delimiter=',', quotechar='|', lineterminator='\n')

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
        datawriter = csv.writer(csvfile, delimiter=',', quotechar='|', lineterminator='\n')

        # Write the interval
        datawriter.writerow([INTERVAL])

        # Write a sawtooth
        write_flat_segment(datawriter, 0.0, t)
        write_flat_segment(datawriter, tallest_bump, t)
        write_ramp_segment(datawriter, tallest_bump, 0.0, -rate)


def gen_square(tallest_bump: float, t=10.0):
    # Open for writing. Do not translate newlines.
    with open(csv_path('square'), mode='w', newline='') as csvfile:
        datawriter = csv.writer(csvfile, delimiter=',', quotechar='|', lineterminator='\n')

        # Write the interval
        datawriter.writerow([INTERVAL])

        # Write a square wave
        write_flat_segment(datawriter, 0.0, t)
        write_flat_segment(datawriter, tallest_bump, t)


# Stress PID controllers, test dropout handling
def gen_stress(tallest_bump=4.0, t=2.0):
    # Open for writing. Do not translate newlines.
    with open(csv_path('stress'), mode='w', newline='') as csvfile:
        datawriter = csv.writer(csvfile, delimiter=',', quotechar='|', lineterminator='\n')

        # Write the interval
        datawriter.writerow([INTERVAL])

        # Start with a long low segment
        write_flat_segment(datawriter, 0.0, 4 * t)

        # Dropout, then resume
        write_dropouts(datawriter, t)
        write_flat_segment(datawriter, tallest_bump, t)

        # Jump to very high segment, with dropout
        write_flat_segment(datawriter, tallest_bump, t)

        # Dropout, then resume
        write_dropouts(datawriter, t)
        write_flat_segment(datawriter, tallest_bump, t)

        # Dropout, then resume at a very different height
        write_dropouts(datawriter, t)
        write_flat_segment(datawriter, 0.0, t)
        write_flat_segment(datawriter, tallest_bump, t)


# Test low signal_quality
def gen_test_signal_quality():
    # Open for writing. Do not translate newlines.
    with open(csv_path('test_signal_quality'), mode='w', newline='') as csvfile:
        datawriter = csv.writer(csvfile, delimiter=',', quotechar='|', lineterminator='\n')

        # Write the interval
        datawriter.writerow([INTERVAL])

        # Start "on the dock"
        write_low_signal_quality(datawriter, t=4)

        # Normal, in the water
        write_flat_segment(datawriter, adj=0.0, t=4)

        # Bad readings
        write_low_signal_quality(datawriter, t=4)

        # Resume, jump
        write_flat_segment(datawriter, adj=2.0, t=4)


def main():
    gen_zeros()
    gen_trapezoid(5.0, 0.2, 20.0)
    gen_sawtooth(1.0, 0.2)
    gen_square(1.0, 20.0)
    gen_stress()
    gen_test_signal_quality()


if __name__ == '__main__':
    main()

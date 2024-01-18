#!/usr/bin/env python3

"""
Read DISTANCE_SENSOR messages and calculate mean and stdev
"""

import argparse
import statistics

from pymavlink import mavutil


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('start', type=float, help='start timestamp')
    parser.add_argument('stop', type=float, help='end timestamp')
    parser.add_argument('path', nargs='+', type=str, help='tlog file')
    args = parser.parse_args()

    for path in args.path:
        print(f'Reading {path}')
        mlog = mavutil.mavlink_connection(path, dialect='ardupilotmega')

        distances = []
        while msg := mlog.recv_match(type='DISTANCE_SENSOR', blocking=False):
            timestamp = getattr(msg, '_timestamp', 0.0)
            if args.start < timestamp < args.stop:
                distances.append(msg.current_distance)

        if len(distances) == 0:
            print(f'No DISTANCE_SENSOR messages found between {args.start} and {args.stop}')
        else:
            xbar = statistics.mean(distances)
            seconds = args.stop - args.start
            print(f'Found {len(distances)} DISTANCE_SENSOR messages over {seconds} seconds, {len(distances) / seconds :.2f} Hz')
            print(f'Mean {xbar :.2f}, stdev {statistics.stdev(distances, xbar) :.2f}')


if __name__ == '__main__':
    main()

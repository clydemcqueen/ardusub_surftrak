#!/usr/bin/env python3

"""
Simulate rangefinder readings and send to mavproxy. QGC must be running.
"""

import argparse
import csv
import os
import time

# Use MAVLink2 wire protocol, must include this before importing pymavlink.mavutil
os.environ['MAVLINK20'] = '1'

from pymavlink import mavutil

from gen_terrain import DROPOUT, LOW_SIGNAL_QUALITY
from sitl_runner import send_distance_sensor_msg, calc_rf, SubZHistory


class RFSender:
    def __init__(self, terrain: str, delay: float):
        print(f'Sending rangefinder readings, {terrain}, delay {delay}')

        self.terrain = terrain
        self.delay = delay
        self.sub_z_history = SubZHistory()

        print('Connect to mavproxy')
        self.conn = mavutil.mavlink_connection(
            'udpin:0.0.0.0:14551', source_system=254, source_component=99, autoreconnect=True)

        print('Wait for HEARTBEAT')
        self.conn.wait_heartbeat()

        print('Ready to send')

    def process_msg(self, msg):
        # Add (time, z) tuples to our z history
        self.sub_z_history.add(time.time(), msg.alt / 1000.0)

    def send_rangefinder_readings(self):
        """
        Send rf readings until we reach the time limit
        """

        # Continue until interrupted
        while True:

            # Re-open the input file so the sequence repeats forever
            with open(self.terrain, newline='') as infile:
                datareader = csv.reader(infile, delimiter=',', quotechar='|')

                # The first input row is the interval
                row = next(datareader)
                interval = float(row[0])

                for row in datareader:
                    # Drain all GLOBAL_POSITION_INT messages
                    while msg := self.conn.recv_match(type='GLOBAL_POSITION_INT', blocking=False):
                        self.process_msg(msg)

                    # Bootstrap: if we don't have enough history, wait for more
                    while self.sub_z_history.length_s() <= self.delay:
                        self.process_msg(self.conn.recv_match(type='GLOBAL_POSITION_INT', blocking=True))

                    # terrain_z is above/below seafloor depth
                    terrain_z = float(row[0])

                    if terrain_z == DROPOUT:
                        print('Drop reading')
                        pass

                    elif terrain_z == LOW_SIGNAL_QUALITY:
                        print('Poor signal quality')
                        send_distance_sensor_msg(self.conn, 555, 10)

                    else:
                        # Get the sub.z reading at time t, where t = now - delay
                        sub_z = self.sub_z_history.get(time.time() - self.delay)
                        assert sub_z is not None

                        rf, signal_quality = calc_rf(terrain_z, sub_z)

                        print(f'{rf :.2f}, {signal_quality}')
                        send_distance_sensor_msg(self.conn, int(rf * 100), signal_quality)

                    time.sleep(interval)


def main():
    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter, description=__doc__)
    parser.add_argument('--terrain', type=str, default='terrain/zeros.csv', help='terrain file')
    parser.add_argument('--delay', type=float, default=0.8, help='sensor delay in seconds')
    args = parser.parse_args()
    sender = RFSender(args.terrain, args.delay)
    sender.send_rangefinder_readings()


if __name__ == '__main__':
    main()

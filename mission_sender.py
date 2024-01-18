#!/usr/bin/env python3

"""
Send a mission to mavproxy
"""

import argparse
import os

# Use MAVLink2 wire protocol, must include this before importing pymavlink.mavutil
os.environ['MAVLINK20'] = '1'

from pymavlink import mavutil

import mission_protocol


def main(path):
    print('Connect to mavproxy')
    conn = mavutil.mavlink_connection(
        'udpin:0.0.0.0:14551', source_system=254, source_component=99, autoreconnect=True)

    print('Wait for HEARTBEAT')
    conn.wait_heartbeat()

    mission_protocol.upload_mission(conn, path)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('path')
    args = parser.parse_args()
    main(args.path)

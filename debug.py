#!/usr/bin/env python3

"""
Listen to MAVLink messages and print some
"""

import time
from pymavlink import mavutil


# Connect to mavproxy in my localhost test
# 14550 is used by QGC, so we'll use 14551
CONN_STR = 'udpin:localhost:14551'

PRINT_FULL = True
# INTERESTING_TYPES = None
INTERESTING_TYPES = ['RANGEFINDER']


def wait_conn(conn):
    recv_msg = None
    while not recv_msg:
        # Wait for a message -- any message will do
        print('Waiting for message on', CONN_STR)
        recv_msg = conn.recv_match()
        if recv_msg:
            print(recv_msg)
        time.sleep(1.0)
    print('Connected!')


def main():
    # This works fine with defaults (source_system=255 and source_component=0)
    conn = mavutil.mavlink_connection(CONN_STR)

    wait_conn(conn)

    while True:
        time.sleep(0.1)
        msg = conn.recv_match(type=INTERESTING_TYPES)
        while msg:
            if PRINT_FULL:
                print(msg, msg.get_msgId(), msg.get_srcSystem(), msg.get_srcComponent())
            else:
                print(msg.get_type(), msg.get_srcSystem(), msg.get_srcComponent())
            msg = conn.recv_match(type=INTERESTING_TYPES)


if __name__ == '__main__':
    main()

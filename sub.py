#!/usr/bin/env python3

import csv
import sys
import time

from pymavlink import mavutil
from pymavlink.dialects.v10.ardupilotmega import\
    MAVLINK_MSG_ID_RANGEFINDER,\
    MAVLINK_MSG_ID_LOCAL_POSITION_NED


# Connect to BlueOS (not tested)
# CONN_STR = 'udpout:localhost:9000'

# Connect to mavproxy in my localhost test
# 14550 is used by QGC, so we'll use 14551
CONN_STR = 'udpin:localhost:14551'

MIN_MEASUREMENT_M = 0.2
MIN_MEASUREMENT_CM = int(MIN_MEASUREMENT_M * 100)

MAX_MEASUREMENT_M = 50.0
MAX_MEASUREMENT_CM = int(MAX_MEASUREMENT_M * 100)

SENSOR_TYPE = mavutil.mavlink.MAV_DISTANCE_SENSOR_UNKNOWN
SENSOR_ID = 1
ORIENTATION = mavutil.mavlink.MAV_SENSOR_ROTATION_PITCH_270  # Downward-facing
COVARIANCE = 255

# Vertical distance from base (sub body origin) to Ping sonar
# TODO depends on what ArduSub uses as body origin -- is it baro_z? Or something else?
BASE_PING_Z = -0.095


class RangefinderSimulator:
    
    def __init__(self, input_name):
        self.input_name = input_name
        self.conn = mavutil.mavlink_connection(CONN_STR)

        # Latest LOCAL_POSITION_NED msg, wait for the EKF to settle, etc.
        self.local_position_ned_msg = None
        # self.wait_for_local_position_ned_msg()

    # Run QGroundControl to get the messages flowing
    # TODO have an option to start the streams w/o QGroundControl running
    def wait_for_local_position_ned_msg(self):
        print(f'Waiting for LOCAL_POSITION_NED msg on {CONN_STR}...')

        while not self.local_position_ned_msg:
            # Flush the queue
            while msg := self.conn.recv_match():
                if msg.get_msgId() == MAVLINK_MSG_ID_LOCAL_POSITION_NED:
                    self.local_position_ned_msg = msg

            if not self.local_position_ned_msg:
                # Pause for a bit
                time.sleep(0.1)

    # Latest sub z position
    def sub_z(self):
        # return -self.local_position_ned_msg.z
        return -0.2

    # Time since boot
    def time_boot_ms(self):
        # return int(self.local_position_ned_msg.time_boot_ms)
        return 0

    # Timestamp, should match the timestamps in tlogs
    def timestamp(self):
        # return getattr(self.local_position_ned_msg, '_timestamp', 0.0)
        return 0.0

    def run(self):
        # Open the output file once
        with open('stamped_terrain.csv', mode='w', newline='') as outfile:
            datawriter = csv.writer(outfile, delimiter=',', quotechar='|')
            datawriter.writerow(['timestamp', 'terrain_z', 'sub_z', 'rf'])
    
            # Continue until the user hits ctrl-C
            while True:

                # Re-open the input file so the sequence repeats forever
                with open(self.input_name, newline='') as infile:
                    datareader = csv.reader(infile, delimiter=',', quotechar='|')
    
                    # The first input row is the interval
                    row = next(datareader)
                    interval = float(row[0])
    
                    for row in datareader:
                        # Get the latest LOCAL_POSITION_NED msg
                        while msg := self.conn.recv_match():
                            if msg.get_msgId() == MAVLINK_MSG_ID_RANGEFINDER:
                                # Debugging: see what ardu* is saying
                                # print(msg)
                                pass
                            elif msg.get_msgId() == MAVLINK_MSG_ID_LOCAL_POSITION_NED:
                                self.local_position_ned_msg = msg

                        # terrain_z is above/below seafloor depth
                        terrain_z = float(row[0])
    
                        # sub_z = -7, terrain_z = -18, reading = 11
                        # Adjust for distance from sub body origin to location of Ping sonar
                        rf = self.sub_z() - terrain_z + BASE_PING_Z

                        if rf < MIN_MEASUREMENT_M:
                            rf = MIN_MEASUREMENT_M
                        elif rf > MAX_MEASUREMENT_M:
                            rf = MAX_MEASUREMENT_M
    
                        print(f'timestamp {self.timestamp()}, terrain_z {terrain_z}, sub_z {self.sub_z()}, rf {rf}')
    
                        # TODO add some noise
                        # TODO model Ping sonar, which has some smoothing and lag
                        # TODO get confidence from log file, pass in as signal_quality
    
                        self.conn.mav.distance_sensor_send(
                            self.time_boot_ms(),
                            MIN_MEASUREMENT_CM,
                            MAX_MEASUREMENT_CM,
                            int(rf * 100),  # Convert m -> cm
                            SENSOR_TYPE,
                            SENSOR_ID,
                            ORIENTATION,
                            COVARIANCE)
    
                        datawriter.writerow([self.timestamp(), terrain_z, self.sub_z(), rf])
                        outfile.flush()
    
                        time.sleep(interval)


def main():
    filename = 'terrain/zeros.csv'
    if len(sys.argv) > 1:
        filename = sys.argv[1]
    print(f'csv file: {filename}')
    
    simulator = RangefinderSimulator(filename)
    simulator.run()
    

if __name__ == '__main__':
    main()

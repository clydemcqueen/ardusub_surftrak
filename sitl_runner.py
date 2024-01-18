#!/usr/bin/env python3

"""
Run an ArduSub simulation.

Interesting sub modes:
      2             alt_hold
      3             auto
      7             circle
     21             rng_hold
"""

import argparse
import csv
import numpy as np
import os
import subprocess
from typing import Optional

from pymavlink.dialects.v20 import ardupilotmega as apm2

# Use MAVLink2 wire protocol, must include this before importing pymavlink.mavutil
os.environ['MAVLINK20'] = '1'

from pymavlink import mavutil

import mavutil2
import mission_protocol
from gen_terrain import DROPOUT, LOW_SIGNAL_QUALITY

PING_NSE = 0.05
PING_DELAY = 0.3

DVL_NSE = 0.01
DVL_DELAY = 0.2


def start_ardusub(speedup: float, heavy: bool):
    ardupilot_home = os.environ.get('ARDUPILOT_HOME')
    model = 'vectored_6dof' if heavy else 'vectored'
    default_params = f'{ardupilot_home}/Tools/autotest/default_params/sub{"-6dof" if heavy else ""}.parm'

    # Using --wipe should do the same thing as -w, but the STAT_BOOTCNT parameter always comes back as 1.
    # This seems like a bug somewhere. See mavutil2.reboot_autopilot for usage.
    subprocess.Popen([
        f'{ardupilot_home}/build/sitl/bin/ardusub',
        '--synthetic-clock',
        '-w',
        '--model', model,
        '--speedup', f'{speedup :.2f}',
        '--defaults', default_params,
        '--sim-address=127.0.0.1',
        '-I0',
        '--home', f'47.607886,-122.344324,-0.1,0.0',
    ])


def send_distance_sensor_msg(conn, distance_cm: int, signal_quality: int):
    """
    Send a DISTANCE_SENSOR msg.

    AP_RangeFinder_MAVLink behaviors:
      * max is the smallest of RNGFND1_MAX_CM (sitl.params) and packet.max_distance_cm (50cm, 0.05m)
      * min is the largest of RNGFND1_MIN_CM (sitl.params) and packet.min_distance_cm (5000cm, 50m)
      * readings outside (min, max) are marked "out of range"
      * covariance is ignored
    """
    conn.mav.distance_sensor_send(
        0, 50, 5000, distance_cm, mavutil.mavlink.MAV_DISTANCE_SENSOR_UNKNOWN, 1,
        mavutil.mavlink.MAV_SENSOR_ROTATION_PITCH_270, 0, signal_quality=signal_quality)


def calc_rf(terrain_z: float, sub_z: float) -> tuple[float, int]:
    """
    Calc rangefinder and signal_quality

    Future: look at attitude and adjust rf
    """

    # Add noise
    rf = sub_z - terrain_z + np.random.normal(scale=PING_NSE)

    # Send signal_quality, typically 100
    signal_quality = 100

    if rf < 0.35:
        rf = 8.888
        signal_quality = 50
    elif rf > 50.0:
        rf = 50.0
        signal_quality = 60

    return rf, signal_quality


class SubZHistory:
    """
    Keep track of recent z readings so that we can simulate a delay
    """

    def __init__(self):
        # History is a list of tuples (t, z)
        self.history: list[tuple[float, float]] = []

    def add(self, t: float, sub_z: float):
        # Should trim older readings to save time and space in long simulations
        self.history.append((t, sub_z))

    def get(self, t: float) -> float or None:
        """
        Return the z reading at time t. Return None if there is no good z reading.
        """
        if len(self.history) == 0:
            return None

        # We can't get a reading in the past
        if t < self.history[0][0]:
            return None

        if len(self.history) == 1:
            return self.history[0][1]

        for i in range(1, len(self.history)):
            if t < self.history[i][0]:
                # We're between 2 readings, interpolate
                t1, d1 = self.history[i - 1]
                t2, d2 = self.history[i]
                return d1 + (d2 - d1) * (t - t1) / (t2 - t1)

        # We fell off the end, use the last reading
        return self.history[len(self.history) - 1][1]

    def length_s(self) -> float:
        """
        Return length of history in seconds
        """
        if len(self.history) < 2:
            return 0.0
        else:
            return self.history[len(self.history) - 1][0] - self.history[0][0]


class SimRunner:
    """
    Manage a simulation.

    Limitation: this class connects directly to ArduSub and does not route MAVLink messages.
    I.e., you cannot use this class with another ground control station like QGroundControl.
    """

    REQUEST_MSGS = {
        apm2.MAVLINK_MSG_ID_VFR_HUD: 10,
        apm2.MAVLINK_MSG_ID_GPS_RAW_INT: 5,
        apm2.MAVLINK_MSG_ID_GLOBAL_POSITION_INT: 5,
    }

    RECV_MSGS = [
        'GLOBAL_POSITION_INT',
        'STATUSTEXT'
    ]

    def __init__(self, speedup: float, duration: int, terrain, delay: float, heavy: bool, depth: float,
                 mission: Optional[str], mode: int, params_file: str):
        # self.clock is used by self.print, so set this early
        self.clock = None

        self.print(f'Run at {speedup}X wall time for {duration} seconds, terrain {terrain}, sensor delay {delay}')

        self.duration = duration
        self.terrain = terrain
        self.delay = delay
        self.depth = depth
        self.mode = mode
        self.sub_z_history = SubZHistory()

        self.print('Start ArduSub')
        start_ardusub(speedup, heavy)

        self.print('Connect to ArduSub')
        self.conn = mavutil.mavlink_connection(
            'tcp:127.0.0.1:5760', source_system=255, source_component=0, autoreconnect=True)

        self.print('Wait for HEARTBEAT')
        self.conn.wait_heartbeat()

        self.print('Set parameters')
        param_list = mavutil2.ParameterList(params_file)
        param_list.set_all(self.conn)

        self.print('Verify parameters')
        param_list.verify_all(self.conn)

        self.print('Reboot')
        mavutil2.reboot_autopilot(self.conn)

        self.print('Fetch parameters')
        param_list.fetch_all(self.conn)

        self.print('Verify parameters')
        param_list.verify_all(self.conn)

        # We are the GCS, so we need to ask for the messages we need
        self.print('Set message intervals')
        for msg_type, msg_rate in SimRunner.REQUEST_MSGS.items():
            mavutil2.set_message_interval(self.conn, msg_type, msg_rate)

        self.print('Wait for GPS fix')
        self.conn.wait_gps_fix()

        if mission and mission != '':
            self.print('Upload mission')
            mission_protocol.upload_mission(self.conn, mission)

        # Continuously send RC inputs to a UDP port
        self.print('Start RC thread')
        self.rc_thread = mavutil2.RCThread(speedup)
        self.rc_thread.start()

        self.print('Start sim clock')
        self.clock = mavutil2.get_sim_clock(self.conn, speedup)

    def print(self, message):
        sim_time = self.clock.rough_time_s() if self.clock else 0.0
        print(f'[{sim_time :.2f}] {message}')

    @staticmethod
    def severity_name(severity: int) -> str:
        if severity == apm2.MAV_SEVERITY_CRITICAL:
            return 'CRITICAL'
        elif severity == apm2.MAV_SEVERITY_WARNING:
            return 'WARNING'
        elif severity == apm2.MAV_SEVERITY_INFO:
            return 'INFO'
        else:
            return 'unknown'

    def process_msg(self, msg):
        if msg.get_type() == 'GLOBAL_POSITION_INT':
            self.clock.update(msg.time_boot_ms)
            self.sub_z_history.add(msg.time_boot_ms * 0.001, msg.relative_alt * 0.001)
        elif msg.get_type() == 'STATUSTEXT':
            self.print(f'{SimRunner.severity_name(msg.severity)}: {msg.text}')

    def send_rangefinder_readings(self):
        """
        Send rf readings until we reach the time limit
        After N readings change modes
        """

        count_readings = 0

        # Open stamped_terrain.csv
        with open('stamped_terrain.csv', mode='w', newline='') as outfile:
            # Write a log with the TimeUS, the terrain_z at that time, the sub_z at that time, and the calculated
            # rf reading. Note that rf reading will appear to arrive at the destination a bit later, controlled
            # by self.delay.
            datawriter = csv.writer(outfile, delimiter=',', quotechar='|', lineterminator='\n')
            datawriter.writerow(['TimeUS', 'terrain_cm', 'sub_cm', 'rf_cm', 'signal_quality'])

            # Continue until we hit the time limit
            while True:

                # Re-open the input file so the sequence repeats forever
                with open(self.terrain, newline='') as infile:
                    datareader = csv.reader(infile, delimiter=',', quotechar='|')

                    # The first input row is the interval
                    row = next(datareader)
                    interval = float(row[0])

                    for row in datareader:
                        # Drain all GLOBAL_POSITION_INT messages and add (z, time_boot_s) tuples to our z history
                        while msg := self.conn.recv_match(type=SimRunner.RECV_MSGS, blocking=False):
                            self.process_msg(msg)

                        # Bootstrap: if we don't have enough history, wait for more
                        while self.sub_z_history.length_s() <= self.delay:
                            self.process_msg(self.conn.recv_match(type=SimRunner.RECV_MSGS, blocking=True))

                        current_time = self.clock.monotonic_time_s()

                        # Get the sub.z reading at time t, where t = now - delay
                        delayed_time = current_time - self.delay
                        sub_z = self.sub_z_history.get(delayed_time)
                        assert sub_z is not None

                        # terrain_z is above/below seafloor depth
                        terrain_z = float(row[0])

                        if terrain_z == DROPOUT:
                            # Do not send a DISTANCE_SENSOR message; note this in the logs
                            rf_cm, signal_quality = -1, -1

                        elif terrain_z == LOW_SIGNAL_QUALITY:
                            rf_cm, signal_quality = 555, 10
                            send_distance_sensor_msg(self.conn, rf_cm, signal_quality)

                        else:
                            rf, signal_quality = calc_rf(terrain_z, sub_z)
                            rf_cm = int(rf * 100.0)
                            send_distance_sensor_msg(self.conn, rf_cm, signal_quality)

                        # Log using delayed_time
                        time_us: int = int(delayed_time * 1000000)
                        datawriter.writerow([time_us, terrain_z * 100.0, sub_z * 100.0, rf_cm, signal_quality])
                        outfile.flush()

                        # At N readings change modes
                        count_readings += 1
                        if count_readings == 10:
                            self.print(f'Set mode to {self.mode}')
                            self.conn.set_mode(self.mode)

                        self.clock.sleep(interval)

                        if self.clock.rough_time_s() > self.duration:
                            return

    def run(self):
        self.print('Set mode to DEPTH_HOLD')
        self.conn.set_mode(2)

        self.print('Arm')
        self.conn.arducopter_arm()
        self.conn.motors_armed_wait()

        self.print(f'Dive to {self.depth}m')
        mavutil2.move_to_depth(self.conn, self.rc_thread, self.depth)

        # Wait for the EKF to produce a good solution (required for CIRCLE and AUTO)
        self.print('Wait for EKF solution')
        self.clock.sleep(25)

        self.print('Send rangefinder readings')
        self.send_rangefinder_readings()

        self.print('Time limit reached')
        self.rc_thread.stop_thread()
        self.rc_thread.join()


def main():
    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter, description=__doc__)
    parser.add_argument('--speedup', type=float, default=1.0, help='SIM_SPEEDUP value')
    parser.add_argument('--time', type=int, default=60, help='How long to run the simulation')
    parser.add_argument('--terrain', type=str, default='terrain/zeros.csv', help='terrain file')
    parser.add_argument('--delay', type=float, default=0.3, help='Sensor delay in seconds, default 0.3')
    parser.add_argument('--heavy', action='store_true', help='Use heavy (6dof) config')
    parser.add_argument('--depth', type=float, default=-10.0, help='Run depth, default -10m')
    parser.add_argument('--mission', type=str, default=None, help='Upload mission items')
    parser.add_argument('--mode', type=int, default=21, help='Mode, default 21 (rng_hold)')
    parser.add_argument('--params', type=str, default='params/sitl.params', help='Params file')
    args = parser.parse_args()
    runner = SimRunner(args.speedup, args.time, args.terrain, args.delay, args.heavy, args.depth, args.mission,
                       args.mode, args.params)
    runner.run()


if __name__ == '__main__':
    main()

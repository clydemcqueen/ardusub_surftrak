#!/usr/bin/env python3

"""
Run an ArduSub simulation.
"""

import argparse
import csv
import os
import subprocess

from pymavlink.dialects.v20 import ardupilotmega as apm2

# Use MAVLink2 wire protocol, must include this before importing pymavlink.mavutil
os.environ['MAVLINK20'] = '1'

from pymavlink import mavutil

import mavutil2
from gen_terrain import DROPOUT, LOW_SIGNAL_QUALITY


def start_ardusub(speedup: float):
    ardupilot_home = os.environ.get('ARDUPILOT_HOME')
    subprocess.Popen([
        f'{ardupilot_home}/build/sitl/bin/ardusub',
        '-S',
        '-w',  # Wipe parameters
        '--model', 'vectored',
        '--speedup', f'{speedup :.2f}',
        '--slave', '0',
        '--defaults', f'{ardupilot_home}/Tools/autotest/default_params/sub.parm',
        '--sim-address=127.0.0.1',
        '-I0',
        '--home', f'47.607886,-122.344324,-0.1,0.0',
    ])


def send_distance_sensor_msg(conn, distance_cm: int, signal_quality: int):
    """
    Send a DISTANCE_SENSOR msg.

    AP_RangeFinder_MAVLink behaviors:
      * max is the smallest of RNGFND1_MAX_CM and packet.max_distance_cm
      * min is the largest of RNGFND1_MIN_CM and packet.min_distance_cm
      * readings outside (min, max) are marked "out of range"
      * covariance is ignored
    """
    conn.mav.distance_sensor_send(
        0, 50, 5000, distance_cm, mavutil.mavlink.MAV_DISTANCE_SENSOR_UNKNOWN, 1,
        mavutil.mavlink.MAV_SENSOR_ROTATION_PITCH_270, 0, signal_quality=signal_quality)


def calc_rf(terrain_z: float, sub_z: float) -> tuple[float, int]:
    """
    Calc rangefinder and signal_quality
    """
    rf = sub_z - terrain_z + -0.095

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

    def __init__(self, speedup: float, duration: int, terrain, delay):
        # self.clock is used by self.print, so set this early
        self.clock = None

        self.print(f'Run at {speedup}X wall time for {duration} seconds, terrain {terrain}, Ping delay {delay}')

        self.duration = duration
        self.terrain = terrain
        self.delay = delay
        self.sub_z_history = SubZHistory()

        self.print('Start ArduSub')
        start_ardusub(speedup)

        self.print('Connect to ArduSub')
        self.conn = mavutil.mavlink_connection(
            'tcp:127.0.0.1:5760', source_system=255, source_component=0, autoreconnect=True)

        self.print('Wait for HEARTBEAT')
        self.conn.wait_heartbeat()

        self.print('Set parameters')
        param_list = mavutil2.ParameterList('params/sitl.params')
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

        self.print('Wait for GLOBAL_POSITION_INT')
        self.clock = mavutil2.get_sim_clock(self.conn, speedup)

        self.print('Wait for GPS fix')
        self.conn.wait_gps_fix()

        # Continuously send RC inputs to a UDP port
        self.print('Start RC thread')
        self.rc_thread = mavutil2.RCThread(speedup)
        self.rc_thread.start()

    def print(self, message):
        sim_time = self.clock.time_since_boot_s() if self.clock else 0.0
        print(f'[{sim_time :.2f}] {message}')

    def send_rangefinder_readings(self):
        """
        Send rf readings until we reach the time limit
        """

        # Open stamped_terrain.csv
        with open('stamped_terrain.csv', mode='w', newline='') as outfile:
            datawriter = csv.writer(outfile, delimiter=',', quotechar='|')
            datawriter.writerow(['TimeUS', 'terrain_z', 'sub_z', 'rf'])

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
                        while gpi_msg := self.conn.recv_match(type='GLOBAL_POSITION_INT', blocking=False):
                            wall_time = getattr(gpi_msg, '_timestamp', 0.0)
                            self.clock.update(gpi_msg.time_boot_ms, wall_time)
                            self.sub_z_history.add(gpi_msg.time_boot_ms / 1000.0, gpi_msg.alt / 1000.0)

                        # Bootstrap: if we don't have enough history, wait for more
                        while self.sub_z_history.length_s() <= self.delay:
                            gpi_msg = self.conn.recv_match(type='GLOBAL_POSITION_INT', blocking=True)
                            wall_time = getattr(gpi_msg, '_timestamp', 0.0)
                            self.clock.update(gpi_msg.time_boot_ms, wall_time)
                            self.sub_z_history.add(gpi_msg.time_boot_ms / 1000.0, gpi_msg.alt / 1000.0)

                        # terrain_z is above/below seafloor depth
                        terrain_z = float(row[0])

                        if terrain_z == DROPOUT:
                            pass

                        elif terrain_z == LOW_SIGNAL_QUALITY:
                            send_distance_sensor_msg(self.conn, 555, 10)

                        else:
                            # Get the sub.z reading at time t, where t = now - delay
                            sub_z = self.sub_z_history.get(self.clock.time_since_boot_s() - self.delay)
                            assert sub_z is not None

                            rf, signal_quality = calc_rf(terrain_z, sub_z)

                            send_distance_sensor_msg(self.conn, int(rf * 100), signal_quality)

                            # For logging purposes, record bad sub_z measurements as 0.0
                            log_sub_z = 0.0 if sub_z is None else sub_z

                            # Generate TimeUS (time-since-boot in microseconds) to match the CTUN msg
                            datawriter.writerow([self.clock.time_since_boot_us(), terrain_z, log_sub_z, rf])
                            outfile.flush()

                        self.clock.sleep(interval)

                        if self.clock.time_since_boot_s() > self.duration:
                            return

    def run(self):
        self.print('Set mode to manual')
        self.conn.set_mode_manual()

        self.print('Arm')
        self.conn.arducopter_arm()
        self.conn.motors_armed_wait()

        self.print('Dive to -10m')
        mavutil2.move_to_depth(self.conn, self.rc_thread, -10)

        self.print('Set mode to RNG_HOLD')
        self.conn.set_mode(21)

        self.print('Send rangefinder readings')
        self.send_rangefinder_readings()

        self.print('Time limit reached')
        self.rc_thread.stop_thread()
        self.rc_thread.join()


def main():
    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter, description=__doc__)
    parser.add_argument('--speedup', type=float, default=1.0, help='SIM_SPEEDUP value')
    parser.add_argument('--time', type=int, default=60, help='how long to run the simulation')
    parser.add_argument('--terrain', type=str, default='terrain/zeros.csv', help='terrain file')
    parser.add_argument('--delay', type=float, default=0.8, help='Ping sensor delay in seconds')
    args = parser.parse_args()
    runner = SimRunner(args.speedup, args.time, args.terrain, args.delay)
    runner.run()


if __name__ == '__main__':
    main()

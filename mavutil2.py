"""
More MAVLink Python utility functions
"""

import os
import struct
import threading
import time

from pymavlink.dialects.v20 import ardupilotmega as apm2

# Use MAVLink2 wire protocol, must include this before importing pymavlink.mavutil
os.environ['MAVLINK20'] = '1'

from pymavlink import mavutil


def get_alt(conn: mavutil.mavfile) -> float:
    return conn.recv_match(type='VFR_HUD', blocking=True).alt


def set_message_interval(conn: mavutil.mavfile, msg_id: int, msg_rate: int):
    conn.mav.send(apm2.MAVLink_command_long_message(
        1, 1, apm2.MAV_CMD_SET_MESSAGE_INTERVAL, 0,
        msg_id, int(1e6 / msg_rate), 0, 0, 0, 0, 0))


class RCThread(threading.Thread):
    """
    Send RC input to ArduSub on port 127.0.0.1:5501.
    """

    def __init__(self, speedup: float):
        threading.Thread.__init__(self)
        self.lock = threading.Lock()
        self.thead_should_quit = False
        self.speedup = speedup
        self.channels = [1500] * 6 + [1000] * 10
        self.udp_port = mavutil.mavudp('127.0.0.1:5501', input=False)

    def run(self):
        while True:
            with self.lock:
                if self.thead_should_quit:
                    break
                self.udp_port.write(struct.pack('<HHHHHHHHHHHHHHHH', *self.channels))

            # Sleep for 0.1s sim time
            time.sleep(0.1 / self.speedup)

    def set_rc_channels(self, throttle):
        with self.lock:
            self.channels[2] = throttle

    def stop_thread(self):
        with self.lock:
            self.thead_should_quit = True


def move_to_depth(conn: mavutil.mavfile, rc_thread: RCThread, target: float):
    alt = get_alt(conn)
    descend = alt > target

    rc_thread.set_rc_channels(1300 if descend else 1700)

    while (alt > target and descend) or (alt < target and not descend):
        alt = get_alt(conn)

    rc_thread.set_rc_channels(1500)


def get_boot_count(conn: mavutil.mavfile):
    """
    Get the value of the STAT_BOOTCNT parameter

    TODO add a timeout
    """
    conn.param_fetch_one('STAT_BOOTCNT')
    while msg := conn.recv_match(type='PARAM_VALUE', blocking=True):
        if msg.param_id == 'STAT_BOOTCNT':
            return int(msg.param_value)


def reboot_autopilot(conn: mavutil.mavfile):
    """
    Reboot the autopilot and verify that it actually happened

    TODO add a timeout
    """
    prev_boot_count = get_boot_count(conn)

    conn.reboot_autopilot()
    conn.wait_heartbeat()

    curr_boot_count = get_boot_count(conn)
    if curr_boot_count - prev_boot_count == 1:
        print(f'STAT_BOOTCNT was {prev_boot_count}, now {curr_boot_count}, reboot detected')
        return
    else:
        raise RebootFailedException(f'STAT_BOOTCNT was {prev_boot_count}, now {curr_boot_count}, reboot not detected')


class SimClock:
    """
    Provide a few tools around the ArduSub time-since-boot clock
    """

    TIME_FACTOR = 0.9  # Be conservative in our estimates

    def __init__(self, speedup: float):
        # Desired speedup
        self.speedup: float = speedup

        # Simulation time in ms from a MAVLink message
        self.msg_time_boot_ms: int = 0

        # Wall time when self.msg_sim_time was last updated
        self.wall_time: float = 0

        # Return value from the last call to monotonic_time_s()
        self.last_monotonic_time_s: float = 0

    def update(self, msg_time_boot_ms: int):
        # Protect against messages out-of-order, delays, etc. (though I've never seen this)
        if msg_time_boot_ms < self.msg_time_boot_ms:
            print('ignore time going backwards')
            return
        elif msg_time_boot_ms == self.msg_time_boot_ms:
            print(f'ignore time standing still')
            return

        self.msg_time_boot_ms = msg_time_boot_ms
        self.wall_time = time.time()

    def rough_time_s(self) -> float:
        """Rough estimate of time-since-boot, may not be monotonic"""
        return self.msg_time_boot_ms / 1000.0 + (time.time() - self.wall_time) * self.speedup

    def conservative_time_s(self) -> float:
        """A more conservative estimate of time-since-boot, may not be monotonic"""
        return self.msg_time_boot_ms / 1000.0 + (time.time() - self.wall_time) * self.speedup * SimClock.TIME_FACTOR

    def monotonic_time_s(self) -> float:
        """Time-since-boot, guaranteed to be monotonic"""
        estimate = self.conservative_time_s()
        if estimate <= self.last_monotonic_time_s:
            # Force monotonicity
            print(f'[{estimate :.2f}] Clock too fast by {self.last_monotonic_time_s - estimate :.4f} seconds')
            estimate = self.last_monotonic_time_s + 0.001

        self.last_monotonic_time_s = estimate
        return estimate

    def sleep(self, d: float):
        time.sleep(d / self.speedup)


def get_sim_clock(conn: mavutil.mavfile, speedup: float) -> SimClock:
    """
    Wait for a GLOBAL_POSITION_INT message and use it to create a SimClock object
    """
    sim_clock = SimClock(speedup)
    gpi_msg = conn.recv_match(type='GLOBAL_POSITION_INT', blocking=True)
    sim_clock.update(gpi_msg.time_boot_ms)
    return sim_clock


class BadParameterValueException(Exception):
    pass


class RebootFailedException(Exception):
    pass


class Parameter:
    def __init__(self, param_id: str, param_value: float, param_type: int):
        self.param_id = param_id
        self.param_value = param_value
        self.param_type = param_type
        self.verified = False  # True if we saw a PARAM_VALUE message with this id and value


class ParameterList:
    @staticmethod
    def parse_param(line: str) -> Parameter or None:
        # Split on whitespace (tabs, spaces)
        fields = line.split()
        return Parameter(fields[2], float(fields[3]), int(fields[4]))

    @staticmethod
    def parse_params(path) -> list[Parameter]:
        result = []
        with open(path) as file:
            for line in file:
                if len(line) < 2 or line.startswith('#'):
                    continue
                param = ParameterList.parse_param(line)
                if param is not None:
                    result.append(param)
        return result

    def __init__(self, path: str):
        """
        Read a set of parameters from a file
        """
        self.params = ParameterList.parse_params(path)

    def set_all(self, conn: mavutil.mavfile):
        """
        Send PARAM_SET messages
        """
        for p in self.params:
            print(f'Set {p.param_id} to {p.param_value}')
            conn.param_set_send(p.param_id, p.param_value)

    def fetch_all(self, conn: mavutil.mavfile):
        """
        Send PARAM_REQUEST_READ messages
        """
        for p in self.params:
            conn.param_fetch_one(p.param_id)

    def verify(self, param_id: str, param_value: float):
        """
        Mark a parameter as verified
        """
        for p in self.params:
            if p.param_id == param_id:
                if p.param_value - param_value < 0.001:
                    p.verified = True
                    return
                else:
                    raise BadParameterValueException(f'{p.param_id} expecting {p.param_value} but got {param_value}')

    def all_verified(self) -> bool:
        """
        Return True if all parameters have been verified
        """
        for p in self.params:
            if not p.verified:
                return False
        return True

    def reset_verified(self):
        """
        Reset the verified flags
        """
        for p in self.params:
            p.verified = False

    def verify_all(self, conn: mavutil.mavfile):
        """
        Listen for PARAM_VALUE messages, and wait until all parameters have been verified

        TODO add a timeout
        """
        self.reset_verified()
        while msg := conn.recv_match(type='PARAM_VALUE', blocking=True):
            self.verify(msg.param_id, msg.param_value)
            if self.all_verified():
                return

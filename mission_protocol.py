"""
Implement the MAVLink mission protocol
"""


import os
import time

from pymavlink.dialects.v20 import ardupilotmega as apm2

# Use MAVLink2 wire protocol, must include this before importing pymavlink.mavutil
os.environ['MAVLINK20'] = '1'

from pymavlink import mavutil, mavwp


def upload_using_mission_protocol(conn, mission_type, items) -> bool:
    start = time.time()

    # Start mission protocol by sending the count of items
    conn.mav.mission_count_send(1, 1, len(items), mission_type)

    remaining_to_send = set(range(0, len(items)))
    sent = set()

    timeout = (10 + len(items) / 10.0)

    while True:
        if time.time() - start > timeout:
            print('Timeout uploading mission')
            return False

        if len(remaining_to_send) == 0:
            print("All sent, waiting for MISSION_ACK")
            break

        # Wait for a MISSION_REQUEST
        m = conn.recv_match(type=['MISSION_REQUEST', 'MISSION_ACK'], blocking=True, timeout=1)
        if m is None:
            continue

        if m.get_type() == 'MISSION_ACK':
            if m.target_system == 255 and m.target_component == 0 and m.type == 1 and m.mission_type == 0:
                print('MAVProxy is messing with us')
                continue
            else:
                print(f'Unexpected MISSION_ACK {str(m)}')
                return False

        print(f'Item {m.seq}/{len(items) - 1} requested')
        print(f'Getting ready to send ({str(items[m.seq])})')

        if m.seq in sent:
            print('Duplicate request, continue')
            continue

        if m.seq not in remaining_to_send:
            print('Item already sent? Or we never had it?')
            return False

        if m.mission_type != mission_type:
            print('Request has wrong mission type')
            return False

        if items[m.seq].mission_type != mission_type:
            print('Input has wrong mission type')
            return False

        if items[m.seq].target_system != 1:
            print('Input has wrong target system')
            return False

        if items[m.seq].target_component != 1:
            print('Input has wrong target component')
            return False

        if items[m.seq].seq != m.seq:
            print(f'Input has wrong sequence number ({items[m.seq].seq} vs {m.seq})')
            return False

        # Pack and send item
        items[m.seq].pack(conn.mav)
        conn.mav.send(items[m.seq])

        remaining_to_send.discard(m.seq)
        sent.add(m.seq)

        timeout += 10  # we received a good request for item; be generous with our timeouts

    m = conn.recv_match(type='MISSION_ACK', blocking=True, timeout=1)

    if m is None:
        print('Timeout waiting for MISSION_ACK')
        return False

    if m.mission_type != mission_type:
        print("MISSION_ACK has wrong mission_type")
        return False

    if m.type != mavutil.mavlink.MAV_MISSION_ACCEPTED:
        print(f'Mission upload failed {mavutil.mavlink.enums["MAV_MISSION_RESULT"][m.type].name}')
        return False

    print(f'Upload of all {len(items)} items succeeded')
    return True


def wp_to_mission_item_int(wp):
    """Convert a MISSION_ITEM to a MISSION_ITEM_INT"""

    if wp.get_type() == 'MISSION_ITEM_INT':
        return wp

    wp_int = mavutil.mavlink.MAVLink_mission_item_int_message(
        wp.target_system,
        wp.target_component,
        wp.seq,
        wp.frame,
        wp.command,
        wp.current,
        wp.autocontinue,
        wp.param1,
        wp.param2,
        wp.param3,
        wp.param4,
        int(wp.x * 1.0e7),
        int(wp.y * 1.0e7),
        wp.z)

    return wp_int


def mission_from_path(path):
    waypoint_loader = mavwp.MAVWPLoader(target_system=1, target_component=1)
    waypoint_loader.load(path)
    return [wp_to_mission_item_int(x) for x in waypoint_loader.wpoints]


# TODO take SimClock
def upload_mission(conn, path) -> bool:
    waypoints = mission_from_path(path)
    return upload_using_mission_protocol(conn, apm2.MAV_MISSION_TYPE_MISSION, waypoints)

#!/usr/bin/env python3
"""
secon26_mission_controller.py

State-machine mission controller for the IEEE SoutheastCon 2026 arena.
Uses Nav2 NavigateToPose to sequence the robot through all tasks.

Arena coordinate system (matches secon26_arena.world):
  Origin (0,0) = center of arena floor
  +Y = North wall, -Y = South wall
  +X = East wall, -X = West wall

Task pose goals:
  Each APPROACH pose brings the robot to the correct facing direction
  for the task (button, crank, keypad, duck collection, etc.)
  The LiDAR-based SLAM keeps localization tight throughout.

State machine sequence (default — adjust order to maximise score):
  1. LEAVE_START       — drive out of start box
  2. ANTENNA4_KEYPAD   — approach Ant#4, face north wall, enter 73738#
  3. ANTENNA1_BUTTON   — approach Ant#1, face south, press button 3x
  4. ANTENNA2_CRANK    — approach Ant#2, face south, rotate crank 540°
  5. COLLECT_DUCKS_AREA1 — sweep Area 1 for random duck
  6. COLLECT_DUCKS_AREA2 — sweep Area 2 for random duck + crater duck
  7. COLLECT_DUCKS_AREA3 — sweep Area 3 for 3 random ducks
  8. CRATER_ENTER       — navigate into crater (score 20pts)
  9. ANTENNA3_DUCK      — remove duck from Ant#3 pressure plate
 10. CRATER_EXIT        — exit crater
 11. LUNAR_LANDING      — deposit all ducks to landing zone
 12. EARTH_COMMS        — transmit antenna LED colours via IR
 13. RETURN_START        — return to starting area (15pts bonus)

Each step sends a NavigateToPose goal.  After reaching the approach pose,
task-specific action nodes take over (button pressing, crank, etc.) —
those are wired through separate action topics handled by the Pi's
peripheral controllers.
"""

import rclpy
from rclpy.node import Node
from rclpy.action import ActionClient
from rclpy.action.client import ClientGoalHandle
from geometry_msgs.msg import PoseStamped, Quaternion
from nav2_msgs.action import NavigateToPose
import math
import time


def make_quaternion(yaw_degrees: float) -> Quaternion:
    """Convert yaw (degrees, CCW from east) to Quaternion."""
    yaw = math.radians(yaw_degrees)
    q = Quaternion()
    q.x = 0.0
    q.y = 0.0
    q.z = math.sin(yaw / 2.0)
    q.w = math.cos(yaw / 2.0)
    return q


def pose(x: float, y: float, yaw_deg: float) -> PoseStamped:
    """Helper to construct a PoseStamped in the map frame."""
    p = PoseStamped()
    p.header.frame_id = 'map'
    p.pose.position.x = x
    p.pose.position.y = y
    p.pose.position.z = 0.0
    p.pose.orientation = make_quaternion(yaw_deg)
    return p


# ─── Arena pose goals ──────────────────────────────────────────────────────────
#
#  Facing conventions (yaw_deg, CCW from +X/east):
#    0°   = facing East  (+X)
#    90°  = facing North (+Y)  ← robot looks toward north wall
#    180° = facing West  (-X)
#    270° = facing South (-Y)  ← robot looks toward south wall
#
#  Approach offsets: robot centre ~20–25cm from antenna face
#  so arm/actuator can reach the task component

TASK_POSES = {
    # ── Antenna #1 (Area 2, upper-left) — button faces SOUTH ──────────────────
    # Robot must face south (270°) and approach from the south side
    'antenna1_approach': pose(-0.80, 0.08, 270.0),   # 27cm south of ant1

    # ── Antenna #2 (Area 3, right) — crank faces SOUTH ────────────────────────
    # Approach from south; robot faces south for left/right crank motion
    'antenna2_left_approach':  pose(0.50, -0.35, 270.0),  # south, for crank
    'antenna2_right_approach': pose(0.50, -0.35, 270.0),  # same approach; crank direction set by driver

    # ── Antenna #3 (inside crater) — pressure plate faces WEST ────────────────
    # Robot descends into crater, approaches from west, faces east (0°)
    'crater_entry':   pose(0.35, 0.15, 0.0),    # enter crater from west edge
    'antenna3_approach': pose(0.52, 0.15, 0.0), # close to ant3, facing east (plate faces west)
    'crater_exit':    pose(0.35, 0.15, 180.0),  # back out to west

    # ── Antenna #4 (Area 1, lower-left) — keypad faces NORTH ──────────────────
    # Robot approaches from north side, faces south (270°) to see the keypad
    'antenna4_approach': pose(-0.80, -0.02, 270.0),  # 23cm north of ant4

    # ── Starting area (centre of 12"×12" green box) ────────────────────────────
    'start_area': pose(-1.067, -0.457, 0.0),

    # ── Lunar landing area (centre of blue zone) ───────────────────────────────
    'lunar_landing': pose(-0.914, 0.305, 270.0),

    # ── Duck collection waypoints (sweeps through each area) ──────────────────
    # Area 1 sweep (bottom-left quadrant, x=-1.22..0, y=-0.61..0)
    'duck_area1_wp1': pose(-0.65, -0.45, 90.0),
    'duck_area1_wp2': pose(-1.05, -0.20, 0.0),

    # Area 2 sweep (top-left quadrant, x=-1.22..0, y=0..0.61)
    'duck_area2_wp1': pose(-0.55, 0.40, 270.0),
    'duck_area2_wp2': pose(-1.05, 0.20, 0.0),

    # Area 3 sweep (right half, x=0..1.22) — 3 ducks expected
    'duck_area3_wp1': pose(0.20, 0.40, 0.0),
    'duck_area3_wp2': pose(0.60, -0.40, 180.0),
    'duck_area3_wp3': pose(1.00, 0.15, 270.0),

    # ── Earth comms position — face the Earth arm (hangs above start side) ────
    # Earth arm is above west wall near starting square; IR transmitter on robot
    # points upward — navigate near the Earth sphere location
    'earth_comms': pose(-1.00, -0.35, 90.0),
}

# Ordered mission sequence (adjust for your strategy)
MISSION_SEQUENCE = [
    'start_area',         # ensure we start in known pose
    'antenna4_approach',  # keypad task (Area 1)
    'antenna1_approach',  # button task (Area 2)
    'antenna2_left_approach',  # crank task (Area 3)
    'duck_area1_wp1',
    'duck_area1_wp2',
    'duck_area2_wp1',
    'duck_area2_wp2',
    'duck_area3_wp1',
    'duck_area3_wp2',
    'duck_area3_wp3',
    'crater_entry',
    'antenna3_approach',  # remove duck from pressure plate
    'crater_exit',
    'lunar_landing',      # deposit ducks
    'earth_comms',        # transmit antenna LED colours via IR
    'start_area',         # return for 15pt bonus
]


class MissionController(Node):
    def __init__(self):
        super().__init__('mission_controller')
        self._nav_client = ActionClient(self, NavigateToPose, 'navigate_to_pose')
        self._current_step = 0
        self._result_received = False
        self._success = False
        self.get_logger().info('Mission controller initialised. Waiting for Nav2...')

    def run(self):
        """Block until Nav2 is available, then execute the mission sequence."""
        self._nav_client.wait_for_server()
        self.get_logger().info('Nav2 ready. Starting mission sequence.')
        # Small delay for SLAM to build initial map
        time.sleep(2.0)
        for step_name in MISSION_SEQUENCE:
            self.get_logger().info(f'── Step: {step_name}')
            target = TASK_POSES[step_name]
            target.header.stamp = self.get_clock().now().to_msg()
            success = self._navigate_to(target)
            if not success:
                self.get_logger().warn(f'Navigation to {step_name} failed — continuing.')
            else:
                self.get_logger().info(f'Reached {step_name}.')
                # TODO: trigger task-specific action here based on step_name
                # e.g. self._do_button_task() for antenna1_approach
                self._post_step_action(step_name)
        self.get_logger().info('Mission sequence complete.')

    def _navigate_to(self, target: PoseStamped) -> bool:
        goal = NavigateToPose.Goal()
        goal.pose = target
        send_future = self._nav_client.send_goal_async(goal)
        rclpy.spin_until_future_complete(self, send_future)
        goal_handle: ClientGoalHandle = send_future.result()
        if not goal_handle.accepted:
            self.get_logger().error('Goal rejected by Nav2')
            return False
        result_future = goal_handle.get_result_async()
        rclpy.spin_until_future_complete(self, result_future)
        return result_future.result().result is not None

    def _post_step_action(self, step_name: str):
        """
        Hook for task-specific actions after reaching a navigation goal.
        Each task type should publish to the appropriate topic or call
        the relevant action server on the Pi's microcontroller bridge.

        Placeholder stubs — fill in with your actuator/peripheral code.
        """
        if step_name == 'antenna1_approach':
            # Button task: press 3 times
            # Publish to /button_press_cmd (count=3)
            self.get_logger().info('[ACTION] Antenna 1 — pressing button 3 times')

        elif step_name == 'antenna2_left_approach':
            # Crank task: rotate 540° clockwise
            # Publish to /crank_cmd (degrees=540, direction='CW')
            self.get_logger().info('[ACTION] Antenna 2 — rotating crank 540°')

        elif step_name == 'antenna3_approach':
            # Pressure plate: remove duck (lift/sweep actuator)
            # Publish to /duck_pickup_cmd
            self.get_logger().info('[ACTION] Antenna 3 — removing duck from pressure plate')

        elif step_name == 'antenna4_approach':
            # Keypad: enter 73738#
            # Publish to /keypad_cmd (sequence='73738#')
            self.get_logger().info('[ACTION] Antenna 4 — entering keypad code 73738#')

        elif step_name == 'lunar_landing':
            # Deposit all collected ducks
            # Publish to /duck_deposit_cmd
            self.get_logger().info('[ACTION] Lunar landing — depositing ducks')

        elif step_name == 'earth_comms':
            # Transmit all 4 antenna LED colours via IR (NEC protocol, addr 0xBB)
            # Publish to /ir_transmit_cmd (list of antenna+colour codes)
            self.get_logger().info('[ACTION] Earth comms — transmitting IR codes')


def main(args=None):
    rclpy.init(args=args)
    node = MissionController()
    try:
        node.run()
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()

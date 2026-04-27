#!/usr/bin/env python3
"""
simple_navigator.py
Simplified autonomous demo mission:

  Trip 1: Duck 1 + Duck 2 -> lunar landing
  Antenna 1: button press x3
  Trip 2: Duck 3 + Duck 4 -> lunar landing
  Trip 3: Duck 5 -> lunar landing
  Trip 4: Crater loop + Duck 6 knock -> lunar landing
  Return to start
"""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from sensor_msgs.msg import LaserScan
from std_srvs.srv import Trigger
import math
import time

# ── Tuning ─────────────────────────────────────────────────────────────────────
LINEAR_SPEED      = 0.12
ANGULAR_SPEED     = 0.4
GOAL_TOLERANCE    = 0.08
HEADING_TOLERANCE = 0.08
OBSTACLE_DIST     = 0.25
FORWARD_ARC       = 0.35

# ── Yaw constants ──────────────────────────────────────────────────────────────
FACE_EAST  = 0.0
FACE_NORTH = 1.5708
FACE_WEST  = 3.1416
FACE_SOUTH = 4.7124

# ── Arena geometry ─────────────────────────────────────────────────────────────
CRATER_X = 1.2192
CRATER_Y = 0.3048
LOOP_R   = 0.45
KNOCK_R  = 0.38

# ── Task poses ─────────────────────────────────────────────────────────────────
TASK_POSES = {
    'start':             (0.15,  0.15,  FACE_EAST),
    'duck1_collect':     (0.762, 0.152, FACE_EAST),
    'duck2_collect':     (0.686, 0.914, FACE_EAST),
    'antenna1_approach': (0.076, 1.00,  FACE_NORTH),
    'duck3_collect':     (1.778, 0.914, FACE_EAST),
    'duck4_collect':     (1.448, 0.610, FACE_EAST),
    'duck5_collect':     (1.778, 0.203, FACE_EAST),
    'crater_south':      (CRATER_X,           CRATER_Y - LOOP_R, FACE_EAST),
    'crater_east':       (CRATER_X + LOOP_R,  CRATER_Y,          FACE_NORTH),
    'crater_north':      (CRATER_X,           CRATER_Y + LOOP_R, FACE_WEST),
    'crater_west':       (CRATER_X - LOOP_R,  CRATER_Y,          FACE_SOUTH),
    'crater_done':       (CRATER_X,           CRATER_Y - LOOP_R, FACE_EAST),
    'duck6_knock':       (CRATER_X + KNOCK_R, CRATER_Y,          FACE_WEST),
    'lunar_landing':     (0.914, 1.067, FACE_SOUTH),
}

MISSION_SEQUENCE = [
    # ── Trip 1: Duck 1 + Duck 2 ──────────────────────────────────────────────
    ('duck1_collect',     'collect'),
    ('duck2_collect',     'collect'),
    ('lunar_landing',     'release'),

    # ── Antenna 1: button press ───────────────────────────────────────────────
    ('antenna1_approach', 'button'),

    # ── Trip 2: Duck 3 + Duck 4 ──────────────────────────────────────────────
    ('duck3_collect',     'collect'),
    ('duck4_collect',     'collect'),
    ('lunar_landing',     'release'),

    # ── Trip 3: Duck 5 ────────────────────────────────────────────────────────
    ('duck5_collect',     'collect'),
    ('lunar_landing',     'release'),

    # ── Trip 4: Crater loop + Duck 6 knock ───────────────────────────────────
    ('crater_south',      None),
    ('crater_east',       None),
    ('crater_north',      None),
    ('crater_west',       None),
    ('crater_done',       'loop_complete'),
    ('duck6_knock',       'knock'),
    ('lunar_landing',     'release'),

    # ── Return to start ───────────────────────────────────────────────────────
    ('start',             None),
]


def angle_diff(a, b):
    d = a - b
    while d > math.pi:  d -= 2 * math.pi
    while d < -math.pi: d += 2 * math.pi
    return d


def yaw_from_quat(q):
    siny = 2.0 * (q.w * q.z + q.x * q.y)
    cosy = 1.0 - 2.0 * (q.y * q.y + q.z * q.z)
    return math.atan2(siny, cosy)


class SimpleNavigator(Node):
    def __init__(self):
        super().__init__('simple_navigator')

        self.cmd_pub = self.create_publisher(Twist, '/cmd_vel', 10)
        self.create_subscription(Odometry, '/odometry/filtered', self.odom_cb, 10)
        self.create_subscription(LaserScan, '/scan', self.scan_cb, 10)

        self._duck_collect = self.create_client(Trigger, '/servo/duck_collect')
        self._duck_release = self.create_client(Trigger, '/servo/duck_release')
        self._button_press = self.create_client(Trigger, '/servo/button_press')
        self._paddle_right = self.create_client(Trigger, '/servo/paddle_right_extend')

        self.x   = 0.0
        self.y   = 0.0
        self.yaw = 0.0
        self.obstacle_ahead = False
        self.ducks_held = 0
        self.pose_received = False

        self.get_logger().info('Simple navigator ready — waiting for odometry...')

    def odom_cb(self, msg):
        self.x   = msg.pose.pose.position.x
        self.y   = msg.pose.pose.position.y
        self.yaw = yaw_from_quat(msg.pose.pose.orientation)
        self.pose_received = True

    def scan_cb(self, msg):
        angle_inc = msg.angle_increment
        center = int((0.0 - msg.angle_min) / angle_inc)
        half_window = int(FORWARD_ARC / angle_inc)
        ranges = [r for r in msg.ranges[max(0, center - half_window):center + half_window]
                  if not math.isinf(r) and not math.isnan(r)]
        self.obstacle_ahead = bool(ranges and min(ranges) < OBSTACLE_DIST)

    def stop(self):
        self.cmd_pub.publish(Twist())

    def call_service(self, client, name):
        if not client.wait_for_service(timeout_sec=2.0):
            self.get_logger().warn(f'{name} not available — skipping')
            return
        future = client.call_async(Trigger.Request())
        rclpy.spin_until_future_complete(self, future, timeout_sec=5.0)

    def drive_to(self, tx, ty, tyaw):
        self.get_logger().info(f'Driving to ({tx:.2f}, {ty:.2f}, {math.degrees(tyaw):.0f}°)')

        # Phase 1 — drive to position
        for _ in range(500):
            rclpy.spin_once(self, timeout_sec=0.05)
            dx = tx - self.x
            dy = ty - self.y
            dist = math.hypot(dx, dy)
            if dist < GOAL_TOLERANCE:
                break
            target_heading = math.atan2(dy, dx)
            heading_error  = angle_diff(target_heading, self.yaw)

            if abs(heading_error) > HEADING_TOLERANCE:
                twist = Twist()
                twist.angular.z = ANGULAR_SPEED if heading_error > 0 else -ANGULAR_SPEED
                self.cmd_pub.publish(twist)
            elif self.obstacle_ahead:
                self.stop()
                self.get_logger().warn('Obstacle — waiting...')
                time.sleep(0.5)
            else:
                twist = Twist()
                twist.linear.x  = LINEAR_SPEED
                twist.angular.z = 0.6 * heading_error
                self.cmd_pub.publish(twist)

        self.stop()
        time.sleep(0.3)

        # Phase 2 — rotate to final heading
        for _ in range(200):
            rclpy.spin_once(self, timeout_sec=0.05)
            heading_error = angle_diff(tyaw, self.yaw)
            if abs(heading_error) < HEADING_TOLERANCE:
                break
            twist = Twist()
            twist.angular.z = ANGULAR_SPEED if heading_error > 0 else -ANGULAR_SPEED
            self.cmd_pub.publish(twist)

        self.stop()
        self.get_logger().info(f'Arrived at ({self.x:.2f}, {self.y:.2f})')

    def execute_action(self, action):
        if action == 'collect':
            self.get_logger().info('[ACTION] Collecting duck')
            self.call_service(self._duck_collect, '/servo/duck_collect')
            self.ducks_held += 1
            self.get_logger().info(f'Ducks held: {self.ducks_held}')

        elif action == 'release':
            self.get_logger().info(f'[ACTION] Releasing {self.ducks_held} ducks at landing zone')
            self.call_service(self._duck_release, '/servo/duck_release')
            self.ducks_held = 0

        elif action == 'button':
            self.get_logger().info('[ACTION] Pressing Antenna 1 button 3 times')
            for i in range(3):
                self.get_logger().info(f'  Press {i+1}/3')
                self.call_service(self._button_press, '/servo/button_press')
                time.sleep(0.8)

        elif action == 'knock':
            self.get_logger().info('[ACTION] Knocking crater duck with right paddle')
            self.call_service(self._paddle_right, '/servo/paddle_right_extend')
            time.sleep(1.0)
            self.call_service(self._duck_collect, '/servo/duck_collect')
            self.ducks_held += 1
            self.get_logger().info(f'Ducks held after knock: {self.ducks_held}')

        elif action == 'loop_complete':
            self.get_logger().info('[ACTION] Crater loop complete — 35pts!')

    def run(self):
        self.get_logger().info('Waiting for odometry...')
        while not self.pose_received:
            rclpy.spin_once(self, timeout_sec=0.1)
        self.get_logger().info('Odometry received — starting demo mission!')
        time.sleep(1.0)

        for pose_key, action in MISSION_SEQUENCE:
            tx, ty, tyaw = TASK_POSES[pose_key]
            self.get_logger().info(f'══ Step: {pose_key}')
            self.drive_to(tx, ty, tyaw)
            if action:
                self.execute_action(action)

        self.get_logger().info('Demo mission complete!')


def main(args=None):
    rclpy.init(args=args)
    node = SimpleNavigator()
    try:
        node.run()
    except KeyboardInterrupt:
        pass
    finally:
        node.stop()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()

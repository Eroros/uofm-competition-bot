#!/usr/bin/env python3
"""
tb6612_driver.py
ROS 2 Humble node for 2x TB6612FNG motor drivers in skid-steer configuration.

Wiring (BCM GPIO numbers):
  Driver 1 — Front wheels
    PWMA (FL speed) : GPIO 12  (Pin 32) — hardware PWM
    AIN1 (FL dir)   : GPIO  5  (Pin 29)
    AIN2 (FL dir)   : GPIO  6  (Pin 31)
    PWMB (FR speed) : GPIO 13  (Pin 33) — hardware PWM
    BIN1 (FR dir)   : GPIO 19  (Pin 35)
    BIN2 (FR dir)   : GPIO 26  (Pin 37)
    STBY            : GPIO 21  (Pin 40)

  Driver 2 — Rear wheels
    PWMA (RL speed) : GPIO 18  (Pin 12) — hardware PWM
    AIN1 (RL dir)   : GPIO 17  (Pin 11)
    AIN2 (RL dir)   : GPIO 27  (Pin 13)
    PWMB (RR speed) : GPIO 25  (Pin 22)
    BIN1 (RR dir)   : GPIO 22  (Pin 15)
    BIN2 (RR dir)   : GPIO 24  (Pin 18)
    STBY            : GPIO 20  (Pin 38)

Subscribes: /cmd_vel (geometry_msgs/Twist)
Publishes:  /odom    (nav_msgs/Odometry)  — dead reckoning from cmd_vel integration
            /tf      (base_footprint → odom)

No encoders — odometry is integrated from velocity commands.
Accuracy improves significantly when fused with IMU via robot_localization EKF.
"""

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist, TransformStamped
from nav_msgs.msg import Odometry
from tf2_ros import TransformBroadcaster
import math
import time

try:
    import RPi.GPIO as GPIO
    HARDWARE = True
except ImportError:
    HARDWARE = False
    print('[tb6612_driver] RPi.GPIO not available — running in simulation mode')

# ── GPIO pin assignments (BCM numbering) ──────────────────────────────────────
# Driver 1 — Front
FL_PWM  = 12
FL_IN1  = 5
FL_IN2  = 6
FR_PWM  = 13
FR_IN1  = 19
FR_IN2  = 26
DRV1_STBY = 21

# Driver 2 — Rear
RL_PWM  = 18
RL_IN1  = 17
RL_IN2  = 27
RR_PWM  = 25
RR_IN1  = 22
RR_IN2  = 24
DRV2_STBY = 20

# ── Robot geometry ────────────────────────────────────────────────────────────
WHEEL_RADIUS   = 0.05   # metres
TRACK_WIDTH    = 0.30   # metres (left to right wheel centre distance)
MAX_SPEED      = 0.20   # m/s at 100% duty cycle — tune to your motors
PWM_FREQ       = 1000   # Hz


class TB6612Driver(Node):
    def __init__(self):
        super().__init__('tb6612_driver')

        # Parameters
        self.declare_parameter('max_speed', MAX_SPEED)
        self.declare_parameter('track_width', TRACK_WIDTH)
        self.max_speed   = self.get_parameter('max_speed').value
        self.track_width = self.get_parameter('track_width').value

        # GPIO setup
        if HARDWARE:
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            pins = [FL_IN1, FL_IN2, FR_IN1, FR_IN2,
                    RL_IN1, RL_IN2, RR_IN1, RR_IN2,
                    FL_PWM, FR_PWM, RL_PWM, RR_PWM,
                    DRV1_STBY, DRV2_STBY]
            for p in pins:
                GPIO.setup(p, GPIO.OUT)
            # Enable both drivers
            GPIO.output(DRV1_STBY, GPIO.HIGH)
            GPIO.output(DRV2_STBY, GPIO.HIGH)
            # PWM instances
            self.pwm_fl = GPIO.PWM(FL_PWM, PWM_FREQ)
            self.pwm_fr = GPIO.PWM(FR_PWM, PWM_FREQ)
            self.pwm_rl = GPIO.PWM(RL_PWM, PWM_FREQ)
            self.pwm_rr = GPIO.PWM(RR_PWM, PWM_FREQ)
            for pwm in [self.pwm_fl, self.pwm_fr, self.pwm_rl, self.pwm_rr]:
                pwm.start(0)
            self.get_logger().info('GPIO initialised — hardware mode')
        else:
            self.get_logger().warn('Simulation mode — no GPIO output')

        # ROS interfaces
        self.cmd_sub = self.create_subscription(Twist, '/cmd_vel', self.cmd_cb, 10)
        self.odom_pub = self.create_publisher(Odometry, '/odom', 10)
        self.tf_broadcaster = TransformBroadcaster(self)

        # Odometry state
        self.x   = 0.0
        self.y   = 0.0
        self.yaw = 0.0
        self.last_time = self.get_clock().now()
        self.last_vx  = 0.0
        self.last_wz  = 0.0

        # Odometry timer — publish at 50Hz
        self.create_timer(0.02, self.publish_odom)

        self.get_logger().info('TB6612 skid-steer driver started')

    def cmd_cb(self, msg: Twist):
        """Convert Twist to left/right wheel speeds and drive motors."""
        vx = msg.linear.x
        wz = msg.angular.z

        self.last_vx = vx
        self.last_wz = wz

        # Skid-steer mixing
        left_speed  = vx - (wz * self.track_width / 2.0)
        right_speed = vx + (wz * self.track_width / 2.0)

        # Normalise to [-1, 1]
        left_duty  = max(-1.0, min(1.0, left_speed  / self.max_speed))
        right_duty = max(-1.0, min(1.0, right_speed / self.max_speed))

        if HARDWARE:
            self._set_motor(self.pwm_fl, FL_IN1, FL_IN2, left_duty)
            self._set_motor(self.pwm_rl, RL_IN1, RL_IN2, left_duty)
            self._set_motor(self.pwm_fr, FR_IN1, FR_IN2, -right_duty)  # right motors reversed
            self._set_motor(self.pwm_rr, RR_IN1, RR_IN2, -right_duty)

    def _set_motor(self, pwm, in1, in2, duty):
        """Set a single motor: duty in [-1.0, 1.0]."""
        dc = abs(duty) * 100.0
        if duty > 0.01:
            GPIO.output(in1, GPIO.HIGH)
            GPIO.output(in2, GPIO.LOW)
        elif duty < -0.01:
            GPIO.output(in1, GPIO.LOW)
            GPIO.output(in2, GPIO.HIGH)
        else:
            GPIO.output(in1, GPIO.LOW)
            GPIO.output(in2, GPIO.LOW)
            dc = 0.0
        pwm.ChangeDutyCycle(dc)

    def publish_odom(self):
        """Dead-reckoning odometry from integrated cmd_vel."""
        now = self.get_clock().now()
        dt  = (now - self.last_time).nanoseconds / 1e9
        self.last_time = now

        # Integrate pose
        self.x   += self.last_vx * math.cos(self.yaw) * dt
        self.y   += self.last_vx * math.sin(self.yaw) * dt
        self.yaw += self.last_wz * dt

        # Quaternion from yaw
        qz = math.sin(self.yaw / 2.0)
        qw = math.cos(self.yaw / 2.0)

        # Publish TF
        tf = TransformStamped()
        tf.header.stamp = now.to_msg()
        tf.header.frame_id = 'odom'
        tf.child_frame_id  = 'base_footprint'
        tf.transform.translation.x = self.x
        tf.transform.translation.y = self.y
        tf.transform.translation.z = 0.0
        tf.transform.rotation.z = qz
        tf.transform.rotation.w = qw
        self.tf_broadcaster.sendTransform(tf)

        # Publish Odometry message
        odom = Odometry()
        odom.header.stamp    = now.to_msg()
        odom.header.frame_id = 'odom'
        odom.child_frame_id  = 'base_footprint'
        odom.pose.pose.position.x = self.x
        odom.pose.pose.position.y = self.y
        odom.pose.pose.orientation.z = qz
        odom.pose.pose.orientation.w = qw
        odom.twist.twist.linear.x  = self.last_vx
        odom.twist.twist.angular.z = self.last_wz
        # Covariance — higher than encoder-based, IMU fusion will tighten this
        odom.pose.covariance[0]  = 0.1
        odom.pose.covariance[7]  = 0.1
        odom.pose.covariance[35] = 0.2
        odom.twist.covariance[0]  = 0.1
        odom.twist.covariance[35] = 0.2
        self.odom_pub.publish(odom)

    def stop_all(self):
        """Emergency stop — called on shutdown."""
        if HARDWARE:
            for pwm in [self.pwm_fl, self.pwm_fr, self.pwm_rl, self.pwm_rr]:
                pwm.ChangeDutyCycle(0)
            GPIO.output(DRV1_STBY, GPIO.LOW)
            GPIO.output(DRV2_STBY, GPIO.LOW)
            GPIO.cleanup()
            self.get_logger().info('Motors stopped, GPIO cleaned up')


def main(args=None):
    rclpy.init(args=args)
    node = TB6612Driver()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.stop_all()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
dsservo_driver.py
ROS 2 Humble driver for 3x DSServo effectors.

Wiring (BCM GPIO):
  Paddle Left  : GPIO 23 (Physical Pin 16)
  Paddle Right : GPIO 16 (Physical Pin 36)
  Crank        : GPIO  7 (Physical Pin 26)

Services:
  /servo/duck_collect        — both paddles sweep inward (capture duck)
  /servo/duck_release        — both paddles open outward (release ducks)
  /servo/button_press        — single paddle tap (press button)
  /servo/crank_turn          — crank sweep 3x (540deg total)
  /servo/paddle_right_extend — right paddle only extends (crater duck knock)

Topics:
  /servo/paddle (Float32) — direct angle control both paddles
  /servo/crank  (Float32) — direct angle control crank
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32
from std_srvs.srv import Trigger
import time
import threading

try:
    import RPi.GPIO as GPIO
    HARDWARE = True
except ImportError:
    HARDWARE = False

# BCM GPIO
PADDLE_LEFT_PIN  = 23
PADDLE_RIGHT_PIN = 16
CRANK_PIN        = 7

# PWM
PWM_FREQ  = 50
MIN_PULSE = 500
MAX_PULSE = 2500

# Servo positions
PADDLE_OPEN    = 90.0   # neutral open position
PADDLE_CLOSED  = 180.0   # inward closed (duck captured)
PADDLE_EXTEND  = 30.0  # outward extended (release or knock)
BUTTON_TAP     = 60.0   # partial close for button press
CRANK_RETRACT  = 0.0
CRANK_EXTEND   = 180.0


def angle_to_duty(angle: float) -> float:
    pulse_us = MIN_PULSE + (angle / 180.0) * (MAX_PULSE - MIN_PULSE)
    return (pulse_us / 20000.0) * 100.0


class DSServoDriver(Node):
    def __init__(self):
        super().__init__('dsservo_driver')

        self.declare_parameter('paddle_trigger_distance', 0.5)
        self.declare_parameter('sweep_duration', 0.5)
        self.declare_parameter('crank_duration', 1.0)

        self.sweep_dur = self.get_parameter('sweep_duration').value
        self.crank_dur = self.get_parameter('crank_duration').value
        self._lock = threading.Lock()
        self._busy = False

        if HARDWARE:
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            for pin in [PADDLE_LEFT_PIN, PADDLE_RIGHT_PIN, CRANK_PIN]:
                GPIO.setup(pin, GPIO.OUT)
            self.pwm_pl = GPIO.PWM(PADDLE_LEFT_PIN,  PWM_FREQ)
            self.pwm_pr = GPIO.PWM(PADDLE_RIGHT_PIN, PWM_FREQ)
            self.pwm_cr = GPIO.PWM(CRANK_PIN,        PWM_FREQ)
            self.pwm_pl.start(angle_to_duty(PADDLE_OPEN))
            self.pwm_pr.start(angle_to_duty(PADDLE_OPEN))
            self.pwm_cr.start(angle_to_duty(CRANK_RETRACT))
            self.get_logger().info('DSServo GPIO initialised — hardware mode')
        else:
            self.get_logger().warn('Simulation mode — no GPIO output')

        # Direct angle topics
        self.create_subscription(Float32, '/servo/paddle', self.paddle_cb, 10)
        self.create_subscription(Float32, '/servo/crank',  self.crank_cb,  10)

        # Services
        self.create_service(Trigger, '/servo/duck_collect',        self.duck_collect_cb)
        self.create_service(Trigger, '/servo/duck_release',        self.duck_release_cb)
        self.create_service(Trigger, '/servo/button_press',        self.button_press_cb)
        self.create_service(Trigger, '/servo/crank_turn',          self.crank_turn_cb)
        self.create_service(Trigger, '/servo/paddle_right_extend', self.paddle_right_extend_cb)

        self.get_logger().info('DSServo driver ready')

    def _set_left(self, angle):
        if HARDWARE:
            self.pwm_pl.ChangeDutyCycle(angle_to_duty(angle))

    def _set_right(self, angle):
        if HARDWARE:
            self.pwm_pr.ChangeDutyCycle(angle_to_duty(angle))

    def _set_crank(self, angle):
        if HARDWARE:
            self.pwm_cr.ChangeDutyCycle(angle_to_duty(angle))

    def _set_both_paddles(self, angle):
        self._set_left(angle)
        self._set_right(angle)

    def paddle_cb(self, msg):
        angle = max(0.0, min(180.0, msg.data))
        self._set_both_paddles(angle)

    def crank_cb(self, msg):
        angle = max(0.0, min(180.0, msg.data))
        self._set_crank(angle)

    def _background(self, fn):
        """Run fn in background thread if not busy."""
        if self._busy:
            return False
        def run():
            with self._lock:
                self._busy = True
                fn()
                self._busy = False
        threading.Thread(target=run, daemon=True).start()
        return True

    def duck_collect_cb(self, request, response):
        """Both paddles sweep inward to capture duck."""
        def action():
            self.get_logger().info('Paddles closing — capturing duck')
            self._set_both_paddles(PADDLE_CLOSED)
            time.sleep(self.sweep_dur)
            # Hold closed to transport duck
        if not self._background(action):
            response.success = False
            response.message = 'Servo busy'
            return response
        response.success = True
        response.message = 'Duck capture initiated'
        return response

    def duck_release_cb(self, request, response):
        """Both paddles open outward to release ducks at landing zone."""
        def action():
            self.get_logger().info('Paddles opening — releasing ducks')
            self._set_both_paddles(PADDLE_EXTEND)
            time.sleep(self.sweep_dur)
            self._set_both_paddles(PADDLE_OPEN)
            time.sleep(0.3)
        if not self._background(action):
            response.success = False
            response.message = 'Servo busy'
            return response
        response.success = True
        response.message = 'Duck release initiated'
        return response

    def button_press_cb(self, request, response):
        """Single paddle tap to press antenna button."""
        def action():
            self.get_logger().info('Paddle tap — pressing button')
            self._set_both_paddles(BUTTON_TAP)
            time.sleep(0.3)
            self._set_both_paddles(PADDLE_OPEN)
            time.sleep(0.3)
        if not self._background(action):
            response.success = False
            response.message = 'Servo busy'
            return response
        response.success = True
        response.message = 'Button press initiated'
        return response

    def crank_turn_cb(self, request, response):
        """Crank sweep x3 for 540deg total rotation."""
        def action():
            self.get_logger().info('Crank: starting 540deg sequence')
            for i in range(3):
                self._set_crank(CRANK_EXTEND)
                time.sleep(self.crank_dur)
                self._set_crank(CRANK_RETRACT)
                time.sleep(self.crank_dur)
            self.get_logger().info('Crank: complete')
        if not self._background(action):
            response.success = False
            response.message = 'Servo busy'
            return response
        response.success = True
        response.message = 'Crank sequence initiated'
        return response

    def paddle_right_extend_cb(self, request, response):
        """Right paddle only extends toward crater to knock Duck 6."""
        def action():
            self.get_logger().info('Right paddle extending — knocking crater duck')
            self._set_right(PADDLE_EXTEND)
            time.sleep(1.0)
            self._set_right(PADDLE_OPEN)
            time.sleep(0.3)
        if not self._background(action):
            response.success = False
            response.message = 'Servo busy'
            return response
        response.success = True
        response.message = 'Right paddle extend initiated'
        return response

    def cleanup(self):
        if HARDWARE:
            self._set_both_paddles(PADDLE_OPEN)
            self._set_crank(CRANK_RETRACT)
            time.sleep(0.3)
            for pwm in [self.pwm_pl, self.pwm_pr, self.pwm_cr]:
                pwm.stop()
            GPIO.cleanup()
            self.get_logger().info('Servos parked, GPIO cleaned up')


def main(args=None):
    rclpy.init(args=args)
    node = DSServoDriver()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.cleanup()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()

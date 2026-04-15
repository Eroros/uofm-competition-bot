#!/usr/bin/env python3
"""
dsservo_driver.py
ROS 2 Humble driver for 3x DSServo effectors.

Wiring (BCM GPIO):
  Paddle Left  : GPIO 23 (Physical Pin 16)
  Paddle Right : GPIO 16 (Physical Pin 36)
  Crank        : GPIO  7 (Physical Pin 26)

All servos are standard PWM: 50Hz, 500-2500us pulse width
  0°   = 500us
  90°  = 1500us
  180° = 2500us

Subscribes:
  /servo/paddle  (std_msgs/Float32) — angle in degrees, both paddles move together
  /servo/crank   (std_msgs/Float32) — angle in degrees

Services:
  /servo/duck_collect  — triggers paddle sweep (90° -> 45° -> 90°)
  /servo/crank_turn    — triggers crank sweep (0° -> 180° -> 0°)

Auto-trigger logic (from README):
  Paddles fire when LiDAR detects object within paddle_trigger_distance (default 0.5m)
  in forward arc. Crank fires when Nav2 signals goal reached.
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

# BCM GPIO pins
PADDLE_LEFT_PIN  = 23
PADDLE_RIGHT_PIN = 16
CRANK_PIN        = 7

# PWM settings
PWM_FREQ    = 50      # Hz
MIN_PULSE   = 500     # us (0 degrees)
MAX_PULSE   = 2500    # us (180 degrees)
RANGE_US    = MAX_PULSE - MIN_PULSE

# Default positions
PADDLE_NEUTRAL = 90.0   # degrees
PADDLE_SWEEP   = 45.0   # degrees — sweep angle for duck collection
CRANK_RETRACT  = 0.0    # degrees
CRANK_EXTEND   = 180.0  # degrees


def angle_to_duty(angle: float) -> float:
    """Convert angle (0-180°) to duty cycle % for 50Hz PWM."""
    pulse_us = MIN_PULSE + (angle / 180.0) * RANGE_US
    return (pulse_us / 20000.0) * 100.0  # 20000us = 1/50Hz period


class DSServoDriver(Node):
    def __init__(self):
        super().__init__('dsservo_driver')

        self.declare_parameter('paddle_trigger_distance', 0.5)
        self.declare_parameter('sweep_duration', 0.5)
        self.declare_parameter('crank_duration', 1.0)

        self.trigger_dist  = self.get_parameter('paddle_trigger_distance').value
        self.sweep_dur     = self.get_parameter('sweep_duration').value
        self.crank_dur     = self.get_parameter('crank_duration').value

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

            self.pwm_pl.start(angle_to_duty(PADDLE_NEUTRAL))
            self.pwm_pr.start(angle_to_duty(PADDLE_NEUTRAL))
            self.pwm_cr.start(angle_to_duty(CRANK_RETRACT))
            self.get_logger().info('DSServo GPIO initialised — hardware mode')
        else:
            self.get_logger().warn('Simulation mode — no GPIO output')

        # Subscribers for direct angle control
        self.create_subscription(Float32, '/servo/paddle', self.paddle_cb, 10)
        self.create_subscription(Float32, '/servo/crank',  self.crank_cb,  10)

        # Services for triggered actions
        self.create_service(Trigger, '/servo/duck_collect', self.duck_collect_cb)
        self.create_service(Trigger, '/servo/crank_turn',   self.crank_turn_cb)

        self.get_logger().info('DSServo driver started')
        self.get_logger().info(f'  Paddle Left  : GPIO {PADDLE_LEFT_PIN} (neutral {PADDLE_NEUTRAL}°)')
        self.get_logger().info(f'  Paddle Right : GPIO {PADDLE_RIGHT_PIN} (neutral {PADDLE_NEUTRAL}°)')
        self.get_logger().info(f'  Crank        : GPIO {CRANK_PIN} (retracted {CRANK_RETRACT}°)')

    def _set_paddle(self, angle: float):
        if HARDWARE:
            dc = angle_to_duty(angle)
            self.pwm_pl.ChangeDutyCycle(dc)
            self.pwm_pr.ChangeDutyCycle(dc)

    def _set_crank(self, angle: float):
        if HARDWARE:
            self.pwm_cr.ChangeDutyCycle(angle_to_duty(angle))

    def paddle_cb(self, msg: Float32):
        """Direct angle control for both paddles."""
        angle = max(0.0, min(180.0, msg.data))
        self._set_paddle(angle)

    def crank_cb(self, msg: Float32):
        """Direct angle control for crank."""
        angle = max(0.0, min(180.0, msg.data))
        self._set_crank(angle)

    def duck_collect_cb(self, request, response):
        """
        Paddle sweep sequence for duck collection:
        neutral (90°) -> sweep (45°) -> neutral (90°)
        Runs in background thread so it doesn't block.
        """
        if self._busy:
            response.success = False
            response.message = 'Servo busy'
            return response

        def sweep():
            with self._lock:
                self._busy = True
                self.get_logger().info('Paddle sweep: collecting duck')
                self._set_paddle(PADDLE_SWEEP)
                time.sleep(self.sweep_dur)
                self._set_paddle(PADDLE_NEUTRAL)
                time.sleep(0.3)
                self._busy = False

        threading.Thread(target=sweep, daemon=True).start()
        response.success = True
        response.message = 'Paddle sweep started'
        return response

    def crank_turn_cb(self, request, response):
        """
        Crank sweep sequence for antenna #2 task:
        retract (0°) -> extend (180°) -> retract (0°)
        540° of real-world crank rotation requires multiple sweeps.
        We do 3 full sweeps to ensure 540° is covered.
        """
        if self._busy:
            response.success = False
            response.message = 'Servo busy'
            return response

        def crank():
            with self._lock:
                self._busy = True
                self.get_logger().info('Crank: starting 540° rotation sequence')
                for i in range(3):
                    self._set_crank(CRANK_EXTEND)
                    time.sleep(self.crank_dur)
                    self._set_crank(CRANK_RETRACT)
                    time.sleep(self.crank_dur)
                self.get_logger().info('Crank: sequence complete')
                self._busy = False

        threading.Thread(target=crank, daemon=True).start()
        response.success = True
        response.message = 'Crank sequence started'
        return response

    def cleanup(self):
        if HARDWARE:
            self._set_paddle(PADDLE_NEUTRAL)
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

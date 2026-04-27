#!/usr/bin/env python3
"""
ky005_ir_driver.py
ROS 2 Humble driver for KY-005 IR Transmitter.

Wiring:
  S (signal) -> Pi Physical Pin 7 (BCM GPIO 4)
  VCC        -> Pi Physical Pin 2 (5V)
  GND        -> Pi Physical Pin 9 (GND)

Uses NEC IR protocol to transmit antenna LED color codes to Earth station.
NEC protocol: 38kHz carrier, address 0xBB (per rulebook)

Color codes (NEC command byte):
  Red    = 0x01
  Green  = 0x02
  Blue   = 0x03
  Yellow = 0x04

Subscribes:
  /rgb/color_name (std_msgs/String) — color detected by TCS34725

Services:
  /ir/transmit_colors — trigger IR transmission of all 4 antenna colors

Topics:
  /ir/transmit (std_msgs/String) — publish color name to transmit manually

Install dependency:
  pip install RPi.GPIO --break-system-packages
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from std_srvs.srv import Trigger
import time
import threading

try:
    import RPi.GPIO as GPIO
    HARDWARE = True
except ImportError:
    HARDWARE = False

# GPIO pin (BCM)
IR_PIN = 4  # Physical Pin 7

# NEC protocol timing (microseconds)
NEC_HDR_MARK  = 9000
NEC_HDR_SPACE = 4500
NEC_BIT_MARK  = 562
NEC_ONE_SPACE = 1688
NEC_ZER_SPACE = 562
NEC_ADDRESS   = 0xBB  # rulebook specified address

# IR carrier frequency
CARRIER_HZ = 38000
CARRIER_PERIOD = 1.0 / CARRIER_HZ

# Color to NEC command mapping
COLOR_CODES = {
    'red':    0x01,
    'green':  0x02,
    'blue':   0x03,
    'yellow': 0x04,
    'white':  0x05,
    'unknown': 0x00,
}


class KY005IRDriver(Node):
    def __init__(self):
        super().__init__('ky005_ir_driver')

        # Store detected antenna colors
        self.antenna_colors = {1: 'unknown', 2: 'unknown', 3: 'unknown', 4: 'unknown'}
        self.current_antenna = 1
        self._lock = threading.Lock()

        if HARDWARE:
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            GPIO.setup(IR_PIN, GPIO.OUT)
            GPIO.output(IR_PIN, GPIO.LOW)
            self.get_logger().info(f'KY-005 IR transmitter on GPIO {IR_PIN}')
        else:
            self.get_logger().warn('Simulation mode — no GPIO output')

        # Subscribe to color detections
        self.create_subscription(String, '/rgb/color_name', self.color_cb, 10)

        # Subscribe to manual transmit commands
        self.create_subscription(String, '/ir/transmit', self.manual_transmit_cb, 10)

        # Service to transmit all antenna colors
        self.create_service(Trigger, '/ir/transmit_colors', self.transmit_colors_cb)

        # Service to advance to next antenna
        self.create_service(Trigger, '/ir/next_antenna', self.next_antenna_cb)

        self.get_logger().info('KY-005 IR driver ready')
        self.get_logger().info(f'Current antenna: {self.current_antenna}')

    def _mark(self, duration_us):
        """Transmit IR carrier for duration_us microseconds."""
        if not HARDWARE:
            return
        end = time.time() + duration_us / 1e6
        while time.time() < end:
            GPIO.output(IR_PIN, GPIO.HIGH)
            time.sleep(CARRIER_PERIOD / 2)
            GPIO.output(IR_PIN, GPIO.LOW)
            time.sleep(CARRIER_PERIOD / 2)

    def _space(self, duration_us):
        """No carrier for duration_us microseconds."""
        if not HARDWARE:
            return
        time.sleep(duration_us / 1e6)

    def _send_nec(self, address, command):
        """Send a single NEC IR frame."""
        self.get_logger().info(f'IR TX: addr=0x{address:02X} cmd=0x{command:02X}')

        # Header
        self._mark(NEC_HDR_MARK)
        self._space(NEC_HDR_SPACE)

        # Address + inverted address + command + inverted command
        data = [address, ~address & 0xFF, command, ~command & 0xFF]
        for byte in data:
            for bit in range(8):
                self._mark(NEC_BIT_MARK)
                if byte & (1 << bit):
                    self._space(NEC_ONE_SPACE)
                else:
                    self._space(NEC_ZER_SPACE)

        # Stop bit
        self._mark(NEC_BIT_MARK)

    def color_cb(self, msg):
        """Store color for current antenna being scanned."""
        color = msg.data
        with self._lock:
            self.antenna_colors[self.current_antenna] = color
        self.get_logger().info(
            f'Antenna {self.current_antenna} color: {color}',
            throttle_duration_sec=2.0
        )

    def manual_transmit_cb(self, msg):
        """Manually transmit a single color code."""
        color = msg.data.lower()
        code = COLOR_CODES.get(color, 0x00)
        threading.Thread(
            target=self._send_nec,
            args=(NEC_ADDRESS, code),
            daemon=True
        ).start()

    def transmit_colors_cb(self, request, response):
        """Transmit all 4 antenna colors to Earth station."""
        def transmit():
            with self._lock:
                colors = dict(self.antenna_colors)

            self.get_logger().info('Transmitting all antenna colors to Earth...')
            for ant_num in range(1, 5):
                color = colors.get(ant_num, 'unknown')
                code  = COLOR_CODES.get(color, 0x00)
                self.get_logger().info(f'  Antenna {ant_num}: {color} (0x{code:02X})')
                self._send_nec(NEC_ADDRESS, code)
                time.sleep(0.1)  # gap between frames

            self.get_logger().info('IR transmission complete')

        threading.Thread(target=transmit, daemon=True).start()
        response.success = True
        response.message = f'Transmitting colors: {self.antenna_colors}'
        return response

    def next_antenna_cb(self, request, response):
        """Advance to next antenna for color scanning."""
        with self._lock:
            self.current_antenna = (self.current_antenna % 4) + 1
        self.get_logger().info(f'Now scanning antenna {self.current_antenna}')
        response.success = True
        response.message = f'Now on antenna {self.current_antenna}'
        return response

    def cleanup(self):
        if HARDWARE:
            GPIO.output(IR_PIN, GPIO.LOW)
            GPIO.cleanup()


def main(args=None):
    rclpy.init(args=args)
    node = KY005IRDriver()
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

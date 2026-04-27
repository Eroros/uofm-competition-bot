#!/usr/bin/env python3
"""
tcs34725_driver.py
ROS 2 Humble driver for TCS34725 RGB Color Sensor via I2C.

Wiring:
  VCC -> Pi Pin 1  (3.3V)
  GND -> Pi Pin 9  (GND)
  SDA -> Pi Pin 3  (GPIO2, I2C bus 1, shared with IMU)
  SCL -> Pi Pin 5  (GPIO3, I2C bus 1, shared with IMU)
  I2C address: 0x29 (fixed)

Publishes:
  /rgb/raw        (std_msgs/ColorRGBA) — raw RGBC values normalized 0-1
  /rgb/color_name (std_msgs/String)    — detected color name for antenna LEDs

Color detection is used to identify antenna LED colors for Earth comms task.
Expected antenna LED colors (from rulebook): Red, Green, Blue, Yellow

Install dependency:
  pip install smbus2 --break-system-packages
"""

import rclpy
from rclpy.node import Node
from std_msgs.msg import ColorRGBA, String
import time

try:
    import smbus2
    HAS_SMBUS = True
except ImportError:
    HAS_SMBUS = False

# TCS34725 I2C address and registers
TCS_ADDR       = 0x29
TCS_CMD        = 0x80
TCS_ENABLE     = 0x00
TCS_ATIME      = 0x01
TCS_CONTROL    = 0x0F
TCS_ID         = 0x12
TCS_STATUS     = 0x13
TCS_CDATAL     = 0x14
TCS_RDATAL     = 0x16
TCS_GDATAL     = 0x18
TCS_BDATAL     = 0x1A

# Enable register bits
TCS_ENABLE_PON = 0x01  # Power on
TCS_ENABLE_AEN = 0x02  # RGBC enable

# Integration time (lower = faster, less accurate)
TCS_ATIME_154MS = 0xC0  # 154ms, 65535 max count
TCS_ATIME_24MS  = 0xF6  # 24ms,  10240 max count

# Gain
TCS_GAIN_1X  = 0x00
TCS_GAIN_4X  = 0x01
TCS_GAIN_16X = 0x02
TCS_GAIN_60X = 0x03

# Color thresholds for LED identification (tune after calibration)
COLOR_THRESHOLDS = {
    'red':    lambda r, g, b: r > 0.4 and r > 2 * g and r > 2 * b,
    'green':  lambda r, g, b: g > 0.4 and g > 2 * r and g > 2 * b,
    'blue':   lambda r, g, b: b > 0.4 and b > 2 * r and b > 2 * g,
    'yellow': lambda r, g, b: r > 0.35 and g > 0.35 and b < 0.2,
    'white':  lambda r, g, b: r > 0.3 and g > 0.3 and b > 0.3,
}


class TCS34725Driver(Node):
    def __init__(self):
        super().__init__('tcs34725_driver')

        self.declare_parameter('i2c_bus',      1)
        self.declare_parameter('publish_rate',  10.0)
        self.declare_parameter('gain',          1)   # 1, 4, 16, or 60

        bus_num = self.get_parameter('i2c_bus').value
        rate    = self.get_parameter('publish_rate').value
        gain    = self.get_parameter('gain').value

        self.raw_pub   = self.create_publisher(ColorRGBA, '/rgb/raw',        10)
        self.name_pub  = self.create_publisher(String,    '/rgb/color_name', 10)

        self.bus = None

        if HAS_SMBUS:
            try:
                self.bus = smbus2.SMBus(bus_num)
                self._init_sensor(gain)
                self.get_logger().info(
                    f'TCS34725 initialised on I2C bus {bus_num}, addr 0x{TCS_ADDR:02X}'
                )
            except Exception as e:
                self.get_logger().error(f'Failed to initialise TCS34725: {e}')
                self.bus = None
        else:
            self.get_logger().warn('smbus2 not installed — run: pip install smbus2 --break-system-packages')

        self.create_timer(1.0 / rate, self.publish_color)

    def _write(self, reg, val):
        self.bus.write_byte_data(TCS_ADDR, TCS_CMD | reg, val)

    def _read_word(self, reg):
        low  = self.bus.read_byte_data(TCS_ADDR, TCS_CMD | reg)
        high = self.bus.read_byte_data(TCS_ADDR, TCS_CMD | reg + 1)
        return (high << 8) | low

    def _init_sensor(self, gain):
        # Verify device ID
        dev_id = self.bus.read_byte_data(TCS_ADDR, TCS_CMD | TCS_ID)
        if dev_id not in [0x44, 0x10]:
            raise RuntimeError(f'Unexpected device ID: 0x{dev_id:02X}')

        # Power on
        self._write(TCS_ENABLE, TCS_ENABLE_PON)
        time.sleep(0.003)

        # Enable RGBC
        self._write(TCS_ENABLE, TCS_ENABLE_PON | TCS_ENABLE_AEN)

        # Set integration time
        self._write(TCS_ATIME, TCS_ATIME_154MS)

        # Set gain
        gain_map = {1: TCS_GAIN_1X, 4: TCS_GAIN_4X, 16: TCS_GAIN_16X, 60: TCS_GAIN_60X}
        self._write(TCS_CONTROL, gain_map.get(gain, TCS_GAIN_1X))
        time.sleep(0.16)  # wait for first integration

    def publish_color(self):
        msg_color = ColorRGBA()
        msg_name  = String()

        if self.bus is not None:
            try:
                c = self._read_word(TCS_CDATAL)  # clear channel
                r = self._read_word(TCS_RDATAL)
                g = self._read_word(TCS_GDATAL)
                b = self._read_word(TCS_BDATAL)

                if c > 0:
                    rn = r / c
                    gn = g / c
                    bn = b / c
                else:
                    rn = gn = bn = 0.0

                msg_color.r = float(rn)
                msg_color.g = float(gn)
                msg_color.b = float(bn)
                msg_color.a = float(c / 65535.0)

                # Identify color
                detected = 'unknown'
                for name, check in COLOR_THRESHOLDS.items():
                    if check(rn, gn, bn):
                        detected = name
                        break

                msg_name.data = detected
                self.get_logger().debug(
                    f'RGB: ({rn:.2f}, {gn:.2f}, {bn:.2f}) → {detected}',
                    throttle_duration_sec=1.0
                )

            except Exception as e:
                self.get_logger().warn(f'TCS34725 read error: {e}', throttle_duration_sec=5.0)

        self.raw_pub.publish(msg_color)
        self.name_pub.publish(msg_name)


def main(args=None):
    rclpy.init(args=args)
    node = TCS34725Driver()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()

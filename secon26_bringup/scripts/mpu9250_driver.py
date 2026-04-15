#!/usr/bin/env python3
"""
mpu9250_driver.py
ROS 2 Humble driver for MPU-9250/6500/9255 IMU via I2C.

Wiring:
  VCC  -> Pi Pin 1  (3.3V)
  GND  -> Pi Pin 6  (GND)
  SDA  -> Pi Pin 3  (GPIO2, I2C1 SDA)
  SCL  -> Pi Pin 5  (GPIO3, I2C1 SCL)
  ADO  -> Pi Pin 6  (GND) -> I2C address 0x68
  INT  -> Pi Pin 11 (GPIO0) — optional interrupt pin

Publishes:
  /imu/data       (sensor_msgs/Imu)
  /imu/mag        (sensor_msgs/MagneticField)

Enable I2C on Pi before use:
  sudo raspi-config -> Interface Options -> I2C -> Enable
  sudo apt install -y python3-smbus2
"""

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu, MagneticField
from geometry_msgs.msg import Vector3
import math
import struct
import time

try:
    import smbus2
    HAS_SMBUS = True
except ImportError:
    HAS_SMBUS = False

# ── MPU-9250 register map ─────────────────────────────────────────────────────
MPU_ADDR        = 0x68   # ADO tied to GND
PWR_MGMT_1      = 0x6B
ACCEL_CONFIG    = 0x1C
GYRO_CONFIG     = 0x1B
ACCEL_XOUT_H    = 0x3B
GYRO_XOUT_H     = 0x43
WHO_AM_I        = 0x75
INT_PIN_CFG     = 0x37
INT_ENABLE      = 0x38

# AK8963 magnetometer (inside MPU-9250)
AK_ADDR         = 0x0C
AK_WHO_AM_I     = 0x00
AK_ST1          = 0x02
AK_HXL          = 0x03
AK_CNTL         = 0x0A
AK_ASAX         = 0x10

# Scale factors
ACCEL_SCALE = 9.81 / 16384.0   # ±2g range -> m/s²
GYRO_SCALE  = math.pi / (180.0 * 131.0)  # ±250°/s range -> rad/s


class MPU9250Driver(Node):
    def __init__(self):
        super().__init__('mpu9250_driver')

        self.declare_parameter('i2c_bus', 1)
        self.declare_parameter('publish_rate', 100.0)
        self.declare_parameter('frame_id', 'imu_link')

        bus_num   = self.get_parameter('i2c_bus').value
        rate      = self.get_parameter('publish_rate').value
        self.frame_id = self.get_parameter('frame_id').value

        self.imu_pub = self.create_publisher(Imu, '/imu/data', 10)
        self.mag_pub = self.create_publisher(MagneticField, '/imu/mag', 10)

        self.bus = None
        self.mag_scale = [1.0, 1.0, 1.0]

        if HAS_SMBUS:
            try:
                self.bus = smbus2.SMBus(bus_num)
                self._init_mpu()
                self._init_ak8963()
                self.get_logger().info(f'MPU-9250 initialised on I2C bus {bus_num}, addr 0x{MPU_ADDR:02X}')
            except Exception as e:
                self.get_logger().error(f'Failed to initialise MPU-9250: {e}')
                self.bus = None
        else:
            self.get_logger().warn('smbus2 not installed — run: sudo apt install python3-smbus2')

        self.create_timer(1.0 / rate, self.publish_imu)

    def _write(self, addr, reg, val):
        self.bus.write_byte_data(addr, reg, val)
        time.sleep(0.001)

    def _read_bytes(self, addr, reg, n):
        return self.bus.read_i2c_block_data(addr, reg, n)

    def _init_mpu(self):
        # Wake up, use PLL gyro clock
        self._write(MPU_ADDR, PWR_MGMT_1, 0x01)
        # Accel ±2g
        self._write(MPU_ADDR, ACCEL_CONFIG, 0x00)
        # Gyro ±250°/s
        self._write(MPU_ADDR, GYRO_CONFIG, 0x00)
        # Enable bypass for AK8963
        self._write(MPU_ADDR, INT_PIN_CFG, 0x02)

    def _init_ak8963(self):
        try:
            # Power down then fuse ROM access
            self._write(AK_ADDR, AK_CNTL, 0x00)
            time.sleep(0.01)
            self._write(AK_ADDR, AK_CNTL, 0x0F)
            time.sleep(0.01)
            # Read sensitivity adjustment
            raw = self._read_bytes(AK_ADDR, AK_ASAX, 3)
            self.mag_scale = [
                (raw[i] - 128) / 256.0 + 1.0 for i in range(3)
            ]
            # Power down then set 16-bit 100Hz continuous
            self._write(AK_ADDR, AK_CNTL, 0x00)
            time.sleep(0.01)
            self._write(AK_ADDR, AK_CNTL, 0x16)
        except Exception as e:
            self.get_logger().warn(f'AK8963 magnetometer init failed: {e}')

    def _read_raw(self, addr, reg):
        raw = self._read_bytes(addr, reg, 6)
        vals = struct.unpack('>3h', bytes(raw))
        return vals

    def publish_imu(self):
        now = self.get_clock().now().to_msg()

        imu_msg = Imu()
        imu_msg.header.stamp    = now
        imu_msg.header.frame_id = self.frame_id

        if self.bus is not None:
            try:
                ax, ay, az = self._read_raw(MPU_ADDR, ACCEL_XOUT_H)
                gx, gy, gz = self._read_raw(MPU_ADDR, GYRO_XOUT_H)

                imu_msg.linear_acceleration.x = ax * ACCEL_SCALE
                imu_msg.linear_acceleration.y = ay * ACCEL_SCALE
                imu_msg.linear_acceleration.z = az * ACCEL_SCALE
                imu_msg.angular_velocity.x    = gx * GYRO_SCALE
                imu_msg.angular_velocity.y    = gy * GYRO_SCALE
                imu_msg.angular_velocity.z    = gz * GYRO_SCALE

                # Orientation unknown without fusion — set covariance -1
                imu_msg.orientation_covariance[0] = -1.0

                # Covariances (empirical for MPU-9250)
                imu_msg.angular_velocity_covariance[0]    = 0.0001
                imu_msg.angular_velocity_covariance[4]    = 0.0001
                imu_msg.angular_velocity_covariance[8]    = 0.0001
                imu_msg.linear_acceleration_covariance[0] = 0.01
                imu_msg.linear_acceleration_covariance[4] = 0.01
                imu_msg.linear_acceleration_covariance[8] = 0.01

                self.imu_pub.publish(imu_msg)

                # Magnetometer
                try:
                    data = self._read_bytes(AK_ADDR, AK_HXL, 7)
                    mx, my, mz = struct.unpack('<3h', bytes(data[:6]))
                    mag_msg = MagneticField()
                    mag_msg.header.stamp    = now
                    mag_msg.header.frame_id = self.frame_id
                    # Convert to Tesla (4912uT full scale / 32760 counts * 1e-6)
                    scale = 4912.0 / 32760.0 * 1e-6
                    mag_msg.magnetic_field.x = mx * scale * self.mag_scale[0]
                    mag_msg.magnetic_field.y = my * scale * self.mag_scale[1]
                    mag_msg.magnetic_field.z = mz * scale * self.mag_scale[2]
                    self.mag_pub.publish(mag_msg)
                except Exception:
                    pass

            except Exception as e:
                self.get_logger().warn(f'IMU read error: {e}', throttle_duration_sec=5.0)
        else:
            # Publish zero IMU when no hardware
            imu_msg.orientation_covariance[0] = -1.0
            self.imu_pub.publish(imu_msg)


def main(args=None):
    rclpy.init(args=args)
    node = MPU9250Driver()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()

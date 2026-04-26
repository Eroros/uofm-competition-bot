"""
stage1_sensors_launch.py
Stage 1 — Sensors only.
Run this first and verify all sensors are publishing before launching Stage 2.

Verify with:
  ros2 topic hz /scan          # should be ~10Hz
  ros2 topic hz /imu/data      # should be ~100Hz
  ros2 topic list              # should show /scan, /imu/data, /imu/mag
"""

import os
from launch import LaunchDescription
from launch.actions import TimerAction
from launch_ros.actions import Node


def generate_launch_description():

    pkg_dir  = os.path.dirname(os.path.realpath(__file__))
    pkg_root = os.path.dirname(pkg_dir)
    urdf_file = os.path.join(pkg_root, 'urdf', 'secon26_bot.urdf')

    with open(urdf_file, 'r') as f:
        robot_desc = f.read()

    # RPLidar C1
    rplidar = Node(
        package='sllidar_ros2',
        executable='sllidar_node',
        name='sllidar_node',
        output='screen',
        parameters=[{
            'serial_port':      '/dev/ttyUSB0',
            'serial_baudrate':  460800,
            'frame_id':         'laser_frame',
            'angle_compensate': True,
            'scan_mode':        'DenseBoost',
	    'channel_type':     'serial',
        }],
        remappings=[('scan', '/scan')]
    )

    # Robot state publisher
    rsp = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[{
            'robot_description': robot_desc,
            'use_sim_time':      False,
        }]
    )

    # MPU-9250 IMU
    imu = Node(
        package='secon26_bringup',
        executable='mpu9250_driver',
        name='mpu9250_driver',
        output='screen',
        parameters=[{
            'i2c_bus':      1,
            'publish_rate': 100.0,
            'frame_id':     'imu_link',
        }]
    )

    return LaunchDescription([
        rplidar,
        rsp,
        # IMU needs I2C to be ready
        TimerAction(period=2.0, actions=[imu]),
    ])

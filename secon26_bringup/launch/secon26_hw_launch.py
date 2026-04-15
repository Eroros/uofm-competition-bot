"""
secon26_hw_launch.py
Hardware bringup — ROS 2 Humble, Raspberry Pi 4, no Gazebo.

Stack:
  1. rplidar_ros       — RPLidar C1 -> /scan
  2. mpu9250_driver    — MPU-9250 IMU -> /imu/data
  3. tb6612_driver     — Motors + dead-reckoning odom -> /odom
  4. robot_state_publisher — URDF -> /tf (static joints)
  5. ekf_filter_node   — Fuse /odom + /imu/data -> /odometry/filtered
  6. slam_toolbox      — Build/load map from /scan + /odometry/filtered
  7. nav2_bringup      — Navigation (commented out until map is saved)

First run workflow:
  1. Launch this file
  2. Drive robot around arena manually (teleop_twist_keyboard)
  3. Save map: ros2 run nav2_map_server map_saver_cli -f ~/secon26_maps/arena_map
  4. Set mode: localization in slam_toolbox_params.yaml
  5. Uncomment Nav2 TimerAction below and relaunch
"""

import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, TimerAction
from launch.substitutions import LaunchConfiguration
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():

    pkg_dir  = os.path.dirname(os.path.realpath(__file__))
    pkg_root = os.path.dirname(pkg_dir)

    urdf_file   = os.path.join(pkg_root, 'urdf',   'secon26_bot.urdf')
    slam_config = os.path.join(pkg_root, 'config', 'slam_toolbox_params.yaml')
    nav2_config = os.path.join(pkg_root, 'config', 'nav2_params.yaml')
    ekf_config  = os.path.join(pkg_root, 'config', 'ekf_params.yaml')

    with open(urdf_file, 'r') as f:
        robot_desc = f.read()

    # ── 1. RPLidar C1 ─────────────────────────────────────────────────────────
    rplidar = Node(
        package='rplidar_ros',
        executable='rplidar_composition',
        name='rplidar_node',
        output='screen',
        parameters=[{
            'serial_port':      '/dev/ttyUSB0',
            'serial_baudrate':  460800,
            'frame_id':         'laser_frame',
            'angle_compensate': True,
            'scan_mode':        'Standard',
        }],
        remappings=[('scan', '/scan')]
    )

    # ── 2. MPU-9250 IMU ───────────────────────────────────────────────────────
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

    # ── 3. TB6612 motor driver ────────────────────────────────────────────────
    motors = Node(
        package='secon26_bringup',
        executable='tb6612_driver',
        name='tb6612_driver',
        output='screen',
        parameters=[{
            'max_speed':   0.20,
            'track_width': 0.30,
        }]
    )

    # ── 4. Robot state publisher ──────────────────────────────────────────────
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

    # ── 5. EKF — fuse odom + IMU ──────────────────────────────────────────────
    ekf = Node(
        package='robot_localization',
        executable='ekf_node',
        name='ekf_filter_node',
        output='screen',
        parameters=[
            ekf_config,
            {'use_sim_time': False},
        ],
        remappings=[
            ('odometry/filtered', '/odometry/filtered'),
        ]
    )

    # ── 6. SLAM Toolbox ───────────────────────────────────────────────────────
    slam = Node(
        package='slam_toolbox',
        executable='async_slam_toolbox_node',
        name='slam_toolbox',
        output='screen',
        parameters=[
            slam_config,
            {'use_sim_time': False},
        ],
        remappings=[
            ('scan', '/scan'),
            ('odom', '/odometry/filtered'),  # use EKF fused odom
        ]
    )

    # ── 7. Nav2 (uncomment after map is saved) ────────────────────────────────
    nav2_dir = get_package_share_directory('nav2_bringup')
    nav2_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(nav2_dir, 'launch', 'navigation_launch.py')
        ),
        launch_arguments={
            'use_sim_time': 'false',
            'autostart':    'true',
            'params_file':  nav2_config,
        }.items()
    )

    return LaunchDescription([
        rplidar,
        rsp,
        motors,

        # IMU starts after I2C is ready
        TimerAction(period=2.0, actions=[imu]),

        # EKF starts after IMU and odom are publishing
        TimerAction(period=4.0, actions=[ekf]),

        # SLAM starts after EKF is producing odometry
        TimerAction(period=6.0, actions=[slam]),

        # Nav2 — uncomment once map is saved and mode set to localization
        # TimerAction(period=10.0, actions=[nav2_launch]),
    ])

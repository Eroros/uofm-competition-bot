"""
secon26_master_launch.py
Master launch file — starts all four stages in sequence with delays.
Use this for competition runs after a map has been built and saved.

For initial map building, run stages manually:
  Terminal 1: ros2 launch secon26_bringup stage1_sensors_launch.py
  Terminal 2: ros2 launch secon26_bringup stage2_localization_launch.py
  Terminal 3: ros2 run teleop_twist_keyboard teleop_twist_keyboard
  (drive around arena to build map)
  ros2 run nav2_map_server map_saver_cli -f ~/secon26_maps/arena_map
  Then set mode: localization in slam_toolbox_params.yaml
  Terminal 4: ros2 launch secon26_bringup stage3_navigation_launch.py
  Terminal 5: ros2 launch secon26_bringup stage4_mission_launch.py

Stage timing:
  0s  — Stage 1: sensors (RPLidar, IMU, RSP)
  15s — Stage 2: localization (motors, EKF, SLAM)
  40s — Stage 3: navigation (Nav2)
  70s — Stage 4: mission (servos, mission controller)
"""

import os
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource


def generate_launch_description():

    pkg_dir = os.path.dirname(os.path.realpath(__file__))

    def stage(filename, delay):
        return TimerAction(
            period=float(delay),
            actions=[
                IncludeLaunchDescription(
                    PythonLaunchDescriptionSource(
                        os.path.join(pkg_dir, filename)
                    )
                )
            ]
        )

    return LaunchDescription([
        stage('stage1_sensors_launch.py',     0),
        stage('stage2_localization_launch.py', 15),
        stage('stage3_navigation_launch.py',   40),
        stage('stage4_mission_launch.py',      70),
    ])

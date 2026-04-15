"""
stage3_navigation_launch.py
Stage 3 — Nav2 navigation stack.
Run ONLY after:
  1. Stage 1 and Stage 2 are running and stable
  2. A map has been saved and slam_toolbox_params.yaml mode set to localization

Verify with:
  ros2 topic list | grep -E "cmd_vel|plan|costmap"
  ros2 node list | grep -E "bt_navigator|controller|planner"

Send a test goal from RViz or:
  ros2 topic pub /goal_pose geometry_msgs/PoseStamped \
    "{header: {frame_id: map}, pose: {position: {x: 0.0, y: 0.0}}}"
"""

import os
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():

    pkg_dir  = os.path.dirname(os.path.realpath(__file__))
    pkg_root = os.path.dirname(pkg_dir)
    nav2_config = os.path.join(pkg_root, 'config', 'nav2_params.yaml')

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
        nav2_launch,
    ])

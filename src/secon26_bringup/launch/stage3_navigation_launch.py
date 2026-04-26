import os
from launch import LaunchDescription
from launch_ros.actions import Node

NAV2_PARAMS = '/home/roho/uofm_competition_robot/uofm-competition-bot/src/secon26_bringup/config/nav2_params.yaml'

LOCAL_COSTMAP = {
    'local_costmap.local_costmap.width': 1.5,
    'local_costmap.local_costmap.height': 1.5,
    'local_costmap.local_costmap.resolution': 0.02,
    'local_costmap.local_costmap.robot_radius': 0.20,
}

GLOBAL_COSTMAP = {
    'global_costmap.global_costmap.width': 3.0,
    'global_costmap.global_costmap.height': 2.0,
    'global_costmap.global_costmap.resolution': 0.02,
    'global_costmap.global_costmap.robot_radius': 0.20,
}

def generate_launch_description():
    return LaunchDescription([
        Node(
            package='nav2_controller',
            executable='controller_server',
            name='controller_server',
            output='screen',
            parameters=[NAV2_PARAMS, LOCAL_COSTMAP],
            remappings=[('cmd_vel', 'cmd_vel_nav')]
        ),
        Node(
            package='nav2_planner',
            executable='planner_server',
            name='planner_server',
            output='screen',
            parameters=[NAV2_PARAMS, GLOBAL_COSTMAP]
        ),
        Node(
            package='nav2_waypoint_follower',
            executable='waypoint_follower',
            name='waypoint_follower',
            output='screen',
            parameters=[NAV2_PARAMS, {'loop_rate': 20.0}]
        ),
        Node(package='nav2_smoother',     executable='smoother_server',  name='smoother_server',  output='screen', parameters=[NAV2_PARAMS]),
        Node(package='nav2_behaviors',    executable='behavior_server',  name='behavior_server',  output='screen', parameters=[NAV2_PARAMS]),
        Node(package='nav2_bt_navigator', executable='bt_navigator',     name='bt_navigator',     output='screen', parameters=[NAV2_PARAMS]),
        Node(package='nav2_velocity_smoother', executable='velocity_smoother', name='velocity_smoother', output='screen', parameters=[NAV2_PARAMS]),
        Node(
            package='nav2_lifecycle_manager',
            executable='lifecycle_manager',
            name='lifecycle_manager_navigation',
            output='screen',
            parameters=[{
                'use_sim_time': False,
                'autostart': True,
                'node_names': [
                    'controller_server',
                    'smoother_server',
                    'planner_server',
                    'behavior_server',
                    'bt_navigator',
                    'waypoint_follower',
                    'velocity_smoother',
                ],
            }]
        ),
    ])

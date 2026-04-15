"""
secon26_sim_launch.py
Targets Gazebo Harmonic + ROS 2 Jazzy (Ubuntu 24.04 dev machine).
For Pi hardware (Humble/Fortress): use secon26_hw_launch.py
"""

import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, ExecuteProcess, TimerAction
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory


def generate_launch_description():

    pkg_dir  = os.path.dirname(os.path.realpath(__file__))
    pkg_root = os.path.dirname(pkg_dir)

    world_file  = os.path.join(pkg_root, 'worlds', 'secon26_arena.world')
    urdf_file   = os.path.join(pkg_root, 'urdf',   'secon26_bot.urdf')
    slam_config = os.path.join(pkg_root, 'config', 'slam_toolbox_params.yaml')
    nav2_config = os.path.join(pkg_root, 'config', 'nav2_params.yaml')

    use_sim_time = LaunchConfiguration('use_sim_time', default='true')
    autostart    = LaunchConfiguration('autostart',    default='true')
    use_rviz     = LaunchConfiguration('use_rviz',     default='true')

    with open(urdf_file, 'r') as f:
        robot_desc = f.read()

    # Gazebo Harmonic
    gz_sim = ExecuteProcess(
        cmd=['gz', 'sim', '-r', world_file],
        output='screen'
    )

    # Bridge: gz topics -> ROS 2
    gz_bridge = Node(
        package='ros_gz_bridge',
        executable='parameter_bridge',
        arguments=[
            '/scan@sensor_msgs/msg/LaserScan[gz.msgs.LaserScan',
            '/odom@nav_msgs/msg/Odometry[gz.msgs.Odometry',
            '/tf@tf2_msgs/msg/TFMessage[gz.msgs.Pose_V',
            '/cmd_vel@geometry_msgs/msg/Twist]gz.msgs.Twist',
            '/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock',
        ],
        output='screen'
    )

    # Spawn robot
    spawn_robot = Node(
        package='ros_gz_sim',
        executable='create',
        arguments=[
            '-name', 'secon26_bot',
            '-string', robot_desc,
            '-x', '-1.067',
            '-y', '-0.457',
            '-z', '0.07',
            '-Y', '0.0',
        ],
        output='screen'
    )

    # Robot state publisher
    rsp = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        name='robot_state_publisher',
        output='screen',
        parameters=[{
            'robot_description': robot_desc,
            'use_sim_time': use_sim_time,
        }]
    )

    # Static TF
    static_tf = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='static_tf_map_odom',
        arguments=['0', '0', '0', '0', '0', '0', 'map', 'odom'],
        output='screen'
    )

    # SLAM Toolbox
    slam = Node(
        package='slam_toolbox',
        executable='async_slam_toolbox_node',
        name='slam_toolbox',
        output='screen',
        parameters=[
            slam_config,
            {'use_sim_time': use_sim_time},
        ],
        remappings=[
            ('scan', '/scan'),
            ('odom', '/odom'),
        ]
    )

    # Nav2
    nav2_dir = get_package_share_directory('nav2_bringup')
    nav2_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(nav2_dir, 'launch', 'navigation_launch.py')
        ),
        launch_arguments={
            'use_sim_time': use_sim_time,
            'autostart': autostart,
            'params_file': nav2_config,
        }.items()
    )

    # RViz2
    rviz = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        condition=IfCondition(use_rviz),
        parameters=[{'use_sim_time': use_sim_time}]
    )

    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='true'),
        DeclareLaunchArgument('autostart',    default_value='true'),
        DeclareLaunchArgument('use_rviz',     default_value='true'),

        gz_sim,
        gz_bridge,
        rsp,
        static_tf,

        TimerAction(period=3.0,  actions=[spawn_robot]),
        TimerAction(period=5.0,  actions=[slam]),
        TimerAction(period=8.0,  actions=[nav2_launch]),
        TimerAction(period=10.0, actions=[rviz]),
    ])

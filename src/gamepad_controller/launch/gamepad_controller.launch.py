from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    """Launch the gamepad controller node with customizable parameters."""

    return LaunchDescription([
        DeclareLaunchArgument('cmd_vel_topic', default_value='/cmd_vel'),
        DeclareLaunchArgument('max_linear_speed', default_value='1.0'),
        DeclareLaunchArgument('max_angular_speed', default_value='2.0'),
        DeclareLaunchArgument('deadzone', default_value='0.1'),
        DeclareLaunchArgument('use_tcp_input', default_value='false'),
        DeclareLaunchArgument('tcp_listen_host', default_value='0.0.0.0'),
        DeclareLaunchArgument('tcp_listen_port', default_value='5005'),
        Node(
            package='gamepad_controller',
            executable='gamepad_controller',
            name='gamepad_controller',
            output='screen',
            parameters=[
                {'cmd_vel_topic': LaunchConfiguration('cmd_vel_topic')},
                {'max_linear_speed': LaunchConfiguration('max_linear_speed')},
                {'max_angular_speed': LaunchConfiguration('max_angular_speed')},
                {'deadzone': LaunchConfiguration('deadzone')},
                {'use_tcp_input': LaunchConfiguration('use_tcp_input')},
                {'tcp_listen_host': LaunchConfiguration('tcp_listen_host')},
                {'tcp_listen_port': LaunchConfiguration('tcp_listen_port')},
            ]
        )
    ])

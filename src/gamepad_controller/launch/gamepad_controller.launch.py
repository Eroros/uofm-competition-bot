from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    """Launch the gamepad controller node with customizable parameters."""
    
    return LaunchDescription([
        Node(
            package='gamepad_controller',
            executable='gamepad_controller',
            name='gamepad_controller',
            output='screen',
            parameters=[
                {'cmd_vel_topic': '/cmd_vel'},
                {'max_linear_speed': 1.0},      # m/s
                {'max_angular_speed': 2.0},     # rad/s
                {'deadzone': 0.1},              # Stick deadzone
            ]
        )
    ])

"""
robot_with_gamepad.launch.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Full hardware bringup WITH remote gamepad controller.

Launch order:
  1. robot_description   — URDF -> robot_state_publisher
  2. robot_drivers       — TB6612FNG motor driver + odometry
  3. robot_effectors     — DSServo paddle/crank controller
  4. gamepad_controller  — Gamepad input -> /cmd_vel
  5. robot_navigation    — Nav2 + LiDAR (optional)

This allows you to drive the robot with a gamepad from a remote PC
while the Pi runs the main bringup.

Usage:
  ros2 launch robot_bringup robot_with_gamepad.launch.py
  ros2 launch robot_bringup robot_with_gamepad.launch.py use_nav:=false
  ros2 launch robot_bringup robot_with_gamepad.launch.py max_linear_speed:=0.5
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():

    use_nav_arg = DeclareLaunchArgument(
        "use_nav", default_value="true",
        description="Launch Nav2 navigation stack",
    )
    use_rviz_arg = DeclareLaunchArgument(
        "use_rviz", default_value="true",
        description="Launch RViz2",
    )
    max_linear_speed_arg = DeclareLaunchArgument(
        "max_linear_speed", default_value="1.0",
        description="Max gamepad linear speed (m/s)",
    )
    max_angular_speed_arg = DeclareLaunchArgument(
        "max_angular_speed", default_value="2.0",
        description="Max gamepad angular speed (rad/s)",
    )

    description_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution(
                [FindPackageShare("robot_description"), "launch", "description.launch.py"]
            )
        )
    )

    drivers_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution(
                [FindPackageShare("robot_drivers"), "launch", "drivers.launch.py"]
            )
        )
    )

    effectors_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution(
                [FindPackageShare("robot_effectors"), "launch", "effectors.launch.py"]
            )
        )
    )

    gamepad_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution(
                [FindPackageShare("gamepad_controller"), "launch", "gamepad_controller.launch.py"]
            )
        ),
        launch_arguments={
            "max_linear_speed":  LaunchConfiguration("max_linear_speed"),
            "max_angular_speed": LaunchConfiguration("max_angular_speed"),
        }.items(),
    )

    nav_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution(
                [FindPackageShare("robot_navigation"), "launch", "navigation.launch.py"]
            )
        ),
        condition=IfCondition(LaunchConfiguration("use_nav")),
        launch_arguments={
            "use_rviz":      LaunchConfiguration("use_rviz"),
            "use_sim_time":  "false",
        }.items(),
    )

    return LaunchDescription([
        use_nav_arg,
        use_rviz_arg,
        max_linear_speed_arg,
        max_angular_speed_arg,
        description_launch,
        drivers_launch,
        effectors_launch,
        gamepad_launch,
        nav_launch,
    ])

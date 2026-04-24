# Gamepad Controller ROS2 Package

Standalone ROS2 package for reading gamepad/XInput controllers and publishing `Twist` commands for remote robot control.

## Quick Start (Local Development PC)

### Installation

```bash
# On your development PC with ROS2 installed
pip install inputs

# Build the package
cd ~/ros2_ws  # Your ROS2 workspace
colcon build --packages-select gamepad_controller
source install/setup.bash
```

### Running Locally

```bash
# Terminal 1: Start your gamepad controller node
ros2 run gamepad_controller gamepad_controller

# Terminal 2 (optional): View the published commands
ros2 topic echo /cmd_vel
```

### Running with Launch File

```bash
ros2 launch gamepad_controller gamepad_controller.launch.py
```

## Controls

| Control | Action |
|---------|--------|
| **Left Stick Y-axis** | Forward/Backward speed |
| **Right Stick X-axis** | Turn left/right |
| **Button A** | Toggle enable/disable |
| **Button B** | Emergency stop (hard-coded to disable) |

## Configuration

Edit parameters in the launch file to adjust:
- `cmd_vel_topic`: Which topic to publish to (default: `/cmd_vel`)
- `max_linear_speed`: Max forward speed in m/s (default: 1.0)
- `max_angular_speed`: Max turn rate in rad/s (default: 2.0)
- `deadzone`: Analog stick deadzone 0-1 (default: 0.1)

## Hardware Requirements

- Any XInput-compatible gamepad (Xbox controller, etc.)
- Development PC running ROS2 Humble

## How It Works

1. Background thread reads gamepad input events using the `inputs` library
2. Main ROS2 control loop (50 Hz) publishes `Twist` messages
3. Analog stick positions are normalized, deadzone-filtered, and scaled
4. Published to `/cmd_vel` for the robot motor driver to consume

## Network Integration

When your robot and development PC are on the same network with matching `ROS_DOMAIN_ID`:

```bash
# On BOTH machines (dev PC and Raspberry Pi):
export ROS_DOMAIN_ID=0
source /opt/ros/humble/setup.bash
```

The gamepad controller will automatically discover the robot's `/cmd_vel` topic and send commands over the network.

---

## Integration Steps (When Ready)

See the main project README for integration instructions.

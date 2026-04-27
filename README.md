# uofm-competition-bot

A starter kit for University of Memphis robotics competitions.

This repository contains the ROS 2 robot stack, hardware notes, simulation assets,
remote/manual control tools, and starter documentation needed to reproduce and
extend the competition robot. The goal is to make each year's work easy to hand
off to the next team.

Project wiki: https://github.com/Eroros/uofm-competition-bot/wiki

## Project Goals

- Modular physical frame
- Sensor skirt / side attachments
- Arduino board mounting
- Grabber and antenna task effectors
- Arm base mounting
- LiDAR mount
- Breadboard and electronics mounting
- Power and core functionality
- Raspberry Pi OS / ROS setup
- Gazebo simulation profile
- Docs, tutorials, and revision procedure
- Add-on / multipurpose modules

# IEEE SoutheastCon 2026 Robot Stack

Autonomous navigation stack for a 4-wheel skid-steer robot competing in the
IEEE SoutheastCon 2026 Hardware Competition. Runs on Raspberry Pi 4 with
ROS 2 Humble.

## Hardware

| Component | Details |
|-----------|---------|
| SBC | Raspberry Pi 4 Model B |
| LiDAR | RPLidar C1 — `/dev/ttyUSB0` |
| IMU | MPU-9250 — I2C bus 1, address 0x68 |
| Drive | 4-wheel skid-steer, 2x TB6612FNG motor drivers |
| Servos | 3x DSServo — 2 paddles (duck collection), 1 crank (antenna task) |
| Sonar | Front-facing — duck proximity detection |
| IR | TX/RX unit — Earth communications (rulebook requirement) |

## Manual and Remote Control

The current manual-control featureset supports two paths:

- ROS gamepad mode: a ROS 2 node reads a local XInput-style controller and
  publishes `geometry_msgs/Twist` on `/cmd_vel`.
- TCP command mode: the Pi runs a TCP receiver inside the same ROS 2 node, and
  another computer runs `tcp_cmd_sender.py` to send simple JSON velocity
  commands.

### Option A: ROS gamepad mode

Use this when the controller is attached to the same machine that is running the
`gamepad_controller` ROS node.

```bash
# Pi or dev machine: start the robot stack with local gamepad input
ros2 launch robot_bringup robot_with_gamepad.launch.py use_nav:=false

# Or run only the gamepad publisher
ros2 run gamepad_controller gamepad_controller
```

Controls:

| Control | Action |
|---------|--------|
| Left stick Y | Forward/backward speed |
| Right stick X | Turn left/right |
| A | Toggle enabled/disabled |
| B | Emergency stop |

### Option B: TCP sender and receiver

Use this when you want a very small transport test, or when the gamepad/sender
computer is not running ROS 2. The receiver converts TCP JSON into `/cmd_vel`.

Start the receiver on the Raspberry Pi:

```bash
cd ~/secon26_ws
source /opt/ros/humble/setup.bash
source install/setup.bash

# Robot hardware stack plus TCP receiver -> /cmd_vel
ros2 launch robot_bringup robot_with_gamepad.launch.py \
  use_nav:=false \
  use_tcp_input:=true \
  tcp_listen_host:=100.100.7.54 \
  tcp_listen_port:=5005
```

To run only the TCP receiver without the rest of the robot bringup:

```bash
ros2 launch gamepad_controller gamepad_controller.launch.py \
  use_tcp_input:=true \
  tcp_listen_host:=100.100.7.54 \
  tcp_listen_port:=5005
```

After pulling changes that affect launch files, rebuild and re-source before
launching:

```bash
cd ~/secon26_ws
colcon build --symlink-install --packages-select gamepad_controller robot_bringup
source install/setup.bash
```

Run the sender from this repository on your laptop/dev PC:

```bash
cd uofm-competition-bot

# Interactive keyboard commands: forward, back, left, right, stop, quit
python tcp_cmd_sender.py --host <PI_IP_ADDRESS> --port 5005

# Send one preset command and exit
python tcp_cmd_sender.py --host <PI_IP_ADDRESS> --port 5005 --once forward
python tcp_cmd_sender.py --host <PI_IP_ADDRESS> --port 5005 --once stop

# Send live gamepad commands over TCP
pip install inputs
python tcp_cmd_sender.py --host <PI_IP_ADDRESS> --port 5005 --gamepad
```

If the sender prints `connection refused`, the IP is reachable but nothing is
listening on port `5005`. Start the TCP receiver first, check that it logs
`TCP input listener started`, and pass the receiver machine's IP with `--host`.

The TCP payload is one JSON object per line:

```json
{"linear":0.15,"angular":0.0}
```

Interactive sender commands:

| Command | Payload |
|---------|---------|
| `forward` | `{"linear":0.15,"angular":0.0}` |
| `back` | `{"linear":-0.15,"angular":0.0}` |
| `left` | `{"linear":0.0,"angular":0.5}` |
| `right` | `{"linear":0.0,"angular":-0.5}` |
| `stop` | `{"linear":0.0,"angular":0.0}` |

You can also type raw JSON in the sender prompt, for example:

```json
{"linear":0.10,"angular":-0.25}
```

---

## GPIO Pin Map (BCM)

### TB6612FNG Driver 1 — Front wheels
| Signal | BCM | Physical Pin |
|--------|-----|-------------|
| PWMA (FL) | 12 | 32 |
| AIN1 (FL) | 5  | 29 |
| AIN2 (FL) | 6  | 31 |
| PWMB (FR) | 13 | 33 |
| BIN1 (FR) | 19 | 35 |
| BIN2 (FR) | 26 | 37 |
| STBY      | 21 | 40 |

### TB6612FNG Driver 2 — Rear wheels
| Signal | BCM | Physical Pin |
|--------|-----|-------------|
| PWMA (RL) | 18 | 12 |
| AIN1 (RL) | 17 | 11 |
| AIN2 (RL) | 27 | 13 |
| PWMB (RR) | 25 | 22 |
| BIN1 (RR) | 22 | 15 |
| BIN2 (RR) | 24 | 18 |
| STBY      | 20 | 38 |

### MPU-9250 IMU
| Signal | BCM | Physical Pin |
|--------|-----|-------------|
| SDA | 2 | 3 |
| SCL | 3 | 5 |
| INT | 0 | 11 |
| ADO | — | 6 (GND → address 0x68) |

### DSServo Effectors
| Servo | BCM | Physical Pin | Default |
|-------|-----|-------------|---------|
| Paddle Left  | 23 | 16 | 90° |
| Paddle Right | 16 | 36 | 90° |
| Crank        | 7  | 26 | 0°  |

---

## Package Layout

```
uofm-competition-bot/
|-- tcp_cmd_sender.py                  # Non-ROS TCP sender for manual tests
|-- quick_motor_test.py                # Direct motor smoke test
|-- quick_servo_test.py                # Direct servo smoke test
|-- src/
|   |-- robot_bringup/                 # Combined robot launch files
|   |-- robot_description/             # URDF/xacro robot model
|   |-- robot_drivers/                 # TB6612 motor driver ROS package
|   |-- robot_effectors/               # Paddle and crank servo controllers
|   |-- robot_navigation/              # Nav2, waypoints, mission helpers
|   |-- robot_simulation/              # Gazebo world and sim package
|   |-- gamepad_controller/            # ROS gamepad node and TCP receiver
|   |-- secon26_bringup/               # Legacy/staged SoutheastCon bringup
|   `-- sllidar_ros2/                  # RPLidar ROS 2 driver
```

---

## Installation (Raspberry Pi 4, Ubuntu 22.04, ROS 2 Humble)

```bash
# 1. Enable I2C for IMU
sudo raspi-config  # Interface Options -> I2C -> Enable
sudo usermod -aG i2c $USER
sudo usermod -aG dialout $USER

# 2. Install ROS 2 dependencies
sudo apt update
sudo apt install -y \
  ros-humble-slam-toolbox \
  ros-humble-nav2-bringup \
  ros-humble-rplidar-ros \
  ros-humble-robot-state-publisher \
  ros-humble-joint-state-publisher \
  ros-humble-tf2-ros \
  ros-humble-robot-localization \
  python3-smbus2

pip install RPi.GPIO inputs

# 3. Clone and build
git clone https://github.com/Eroros/uofm-competition-bot.git ~/secon26_ws
cd ~/secon26_ws
source /opt/ros/humble/setup.bash
colcon build --symlink-install
source install/setup.bash
```

---

## Launch Workflow

### First run — build the map

Open 3 terminals on the Pi:

```bash
# Terminal 1 — sensors
ros2 launch secon26_bringup stage1_sensors_launch.py

# Terminal 2 — localization (after Terminal 1 is stable)
ros2 launch secon26_bringup stage2_localization_launch.py

# Terminal 3 — drive around arena to build map
sudo apt install -y ros-humble-teleop-twist-keyboard
ros2 run teleop_twist_keyboard teleop_twist_keyboard
```

Save the map once arena is fully covered:
```bash
mkdir -p ~/secon26_maps
ros2 run nav2_map_server map_saver_cli -f ~/secon26_maps/arena_map
```

### Switch to localization mode

Edit `config/slam_toolbox_params.yaml`:
```yaml
mode: localization
map_file_name: /home/jawn/secon26_maps/arena_map
```

### Competition run — full autonomous stack

```bash
# All stages in sequence (use after map is saved)
ros2 launch secon26_bringup secon26_master_launch.py
```

Or manually stage by stage:
```bash
# Terminal 1
ros2 launch secon26_bringup stage1_sensors_launch.py
# Terminal 2 (after ~15s)
ros2 launch secon26_bringup stage2_localization_launch.py
# Terminal 3 (after ~40s)
ros2 launch secon26_bringup stage3_navigation_launch.py
# Terminal 4 (after ~70s)
ros2 launch secon26_bringup stage4_mission_launch.py
```

---

## Arena Layout

```
 West ←──────────── 8ft (2.44m) ────────────→ East
 ┌──────────────────────┬──────────────────────┐  ↑
 │  Area 2 (green)      │  Area 3 (purple)     │  │
 │  Antenna #1 (button) │  Antenna #2 (crank)  │  │
 │  Lunar Landing [blue]│                      │  4ft
 ├──────────────────────┤   Area 4 ●CRATER     │  │
 │  Area 1 (blue)       │   Antenna #3 (plate) │  │
 │  START [green]       │                      │  │
 │  Antenna #4 (keypad) │                      │  ↓
 └──────────────────────┴──────────────────────┘
  ↑ South wall
```

### Antenna orientations
| Antenna | Task | Faces | Robot approach |
|---------|------|-------|----------------|
| #1 | Button (3 presses) | South | Face south (270°) |
| #2 | Crank (540°) | South | Face south (270°) |
| #3 | Pressure plate | West | Face east (0°) |
| #4 | Keypad (73738#) | North | Face south (270°) |

---

## Key ROS 2 Topics

| Topic | Type | Node |
|-------|------|------|
| `/scan` | LaserScan | rplidar_ros |
| `/imu/data` | Imu | mpu9250_driver |
| `/odom` | Odometry | tb6612_driver |
| `/odometry/filtered` | Odometry | ekf_filter_node |
| `/map` | OccupancyGrid | slam_toolbox |
| `/cmd_vel` | Twist | Nav2 controller |
| `/servo/paddle` | Float32 | dsservo_driver |
| `/servo/crank` | Float32 | dsservo_driver |
| `/navigate_to_pose` | Action | bt_navigator |

## Key ROS 2 Services

| Service | Node |
|---------|------|
| `/servo/duck_collect` | dsservo_driver |
| `/servo/crank_turn` | dsservo_driver |

---

## Tuning Task Approach Poses

All competition task poses are in `secon26_mission_controller.py` → `TASK_POSES`.

To find the correct pose:
1. Launch Stage 1 and Stage 2
2. Manually drive to exact position and heading
3. Echo current pose: `ros2 topic echo /odometry/filtered --once`
4. Compute yaw from quaternion:
   ```python
   import math; math.degrees(2 * math.atan2(z, w))
   ```
5. Update `TASK_POSES` with x, y, yaw_degrees

---

## Scoring Reference

| Task | Points | Priority |
|------|--------|----------|
| Leave start area | 10 | ★★★★★ |
| Auto-start (LED bar) | 15 | ★★★★★ |
| Each antenna on (×4) | 60 | ★★★★★ |
| Each duck in landing (×6) | 30 | ★★★★☆ |
| Antenna LED to Earth (×4) | 120 | ★★★★☆ |
| First Earth connection | 20 | ★★★☆☆ |
| Enter crater | 20 | ★★★☆☆ |
| Crater lap | 35 | ★★☆☆☆ |
| Return to start | 15 | ★★☆☆☆ |
| Plant flag | 10 | ★★☆☆☆ |
| **Max total** | **430** | |

# secon26_bringup — IEEE SoutheastCon 2026 Robot Stack

LiDAR-only navigation for a 4ft × 8ft arena using:
- **RPLidar C1** — primary sensing (replaces TOF, ultrasonic, optical flow, line tracker)
- **slam_toolbox** — online async SLAM → occupancy map
- **Nav2** — global/local planning + behaviour trees
- **Gazebo Harmonic** — full arena simulation
- **Front sonar** — duck proximity detection only (kept, not replaced by LiDAR)
- **IR unit** — Earth comms only (kept)

---

## Arena layout reference

```
 West wall ←─────────────── 8ft (2.44m) ───────────────→ East wall
 ┌──────────────────────────┬──────────────────────────────┐  ↑
 │  Area 2 (green)          │  Area 3 (purple)             │  │
 │  Antenna #1 (button)  ●  │  Antenna #2 (crank)  ●       │  │
 │  Lunar Landing [blue]    │                              │  4ft
 ├──────────────────────────┤      Area 4 (red) ●CRATER    │  │
 │  Area 1 (blue)           │      Antenna #3 (duck plate) │  │
 │  START [green]  ●        │                              │  │
 │  Antenna #4 (keypad) ●   │                              │  ↓
 └──────────────────────────┴──────────────────────────────┘
  ↑ South wall (antennas 1 & 2 face south)
```

Antenna orientations (what face the robot must align to):
| Antenna | Task   | Faces  | Robot approach direction |
|---------|--------|--------|--------------------------|
| #1      | Button | South  | Robot faces south (270°) |
| #2      | Crank  | South  | Robot faces south (270°) |
| #3      | Duck plate | West | Robot faces east (0°)  |
| #4      | Keypad | North  | Robot faces south (270°) |

---

## Installation (Pi 5 / Pi 4 with Ubuntu 22.04 + ROS 2 Humble)

```bash
# 1. Create workspace
mkdir -p ~/secon26_ws/src
cd ~/secon26_ws/src
# copy this package here

# 2. Install dependencies
sudo apt update
sudo apt install -y \
  ros-humble-slam-toolbox \
  ros-humble-nav2-bringup \
  ros-humble-rplidar-ros \
  ros-humble-robot-state-publisher \
  ros-humble-joint-state-publisher \
  ros-humble-ros-gz-bridge \
  ros-humble-ros-gz-sim \
  ros-humble-tf2-ros \
  ros-humble-robot-localization

# 3. Build
cd ~/secon26_ws
colcon build --symlink-install
source install/setup.bash
```

---

## Workflow

### Step 1 — Simulation

```bash
# Launch full sim (Gazebo + SLAM + Nav2 + RViz)
ros2 launch secon26_bringup secon26_sim_launch.py

# In RViz: use "2D Goal Pose" tool to drive the robot around the arena
# SLAM builds the map automatically
```

### Step 2 — Save the map (once arena is fully mapped)

```bash
mkdir -p ~/secon26_maps
ros2 run nav2_map_server map_saver_cli \
  -f ~/secon26_maps/arena_map \
  --ros-args -p save_map_timeout:=5.0
```

### Step 3 — Switch to localization mode

Edit `config/slam_toolbox_params.yaml`:
```yaml
mode: localization          # was: mapping
map_file_name: /home/pi/secon26_maps/arena_map
```

### Step 4 — Hardware bringup on Pi

```bash
# Grant LiDAR port access
sudo usermod -aG dialout $USER && newgrp dialout

# Launch hardware stack
ros2 launch secon26_bringup secon26_hw_launch.py
```

### Step 5 — Run the mission

```bash
# Run mission controller (after Nav2 is ready ~10s)
ros2 run secon26_bringup secon26_mission_controller
```

---

## Tuning task approach poses

All approach poses are in `secon26_mission_controller.py` → `TASK_POSES`.

To find the correct pose for each task:
1. Launch hardware stack
2. Manually drive the robot to the exact position/heading you want
3. Echo the current pose:
   ```bash
   ros2 topic echo /amcl_pose --once
   ```
4. Copy x, y, and compute yaw_degrees from quaternion z/w:
   ```python
   import math; math.degrees(2 * math.atan2(z, w))
   ```
5. Update `TASK_POSES` accordingly

---

## What LiDAR handles (replacing old sensors)

| Old sensor              | Replaced by                              |
|-------------------------|------------------------------------------|
| Time-of-flight (×N)     | slam_toolbox costmap — wall distances    |
| Ultrasonic (most)       | Nav2 local costmap obstacle avoidance    |
| Optical flow            | SLAM odom fusion — pose estimation       |
| Line tracking sensor    | LiDAR-based zone detection via costmap   |

**Kept (not replaced):**
- Front sonar — duck proximity (short range, narrow cone)
- IR TX/RX — Earth communications (required by rulebook)

---

## Key topics

| Topic              | Type                   | Publisher         |
|--------------------|------------------------|-------------------|
| `/scan`            | LaserScan              | rplidar_ros       |
| `/odom`            | Odometry               | diff_drive ctrl   |
| `/map`             | OccupancyGrid          | slam_toolbox      |
| `/tf`              | TFMessage              | slam_toolbox+rsp  |
| `/cmd_vel`         | Twist                  | Nav2 controller   |
| `/navigate_to_pose`| Action (NavigateToPose)| Nav2 bt_navigator |
| `/sonar_front`     | LaserScan              | sonar driver      |

---

## Scoring strategy (reference)

| Task                        | Points | Priority |
|-----------------------------|--------|----------|
| Leave start area            | 10     | ★★★★★   |
| Auto-start (LED bar)        | 15     | ★★★★★   |
| Each antenna turned on (×4) | 60     | ★★★★★   |
| Each duck in landing (×6)   | 30     | ★★★★☆   |
| Antenna LED to Earth (×4)   | 120    | ★★★★☆   |
| First Earth connection      | 20     | ★★★☆☆   |
| Enter crater                | 20     | ★★★☆☆   |
| Crater lap                  | 35     | ★★☆☆☆   |
| Return to start             | 15     | ★★☆☆☆   |
| Plant flag                  | 10     | ★★☆☆☆   |
| **Max total**               | **430**|          |

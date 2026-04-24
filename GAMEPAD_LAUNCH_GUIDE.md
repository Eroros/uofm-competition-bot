# Gamepad Controller Setup & Launch Guide

## Quick Start Overview

- **Raspberry Pi (Robot)**: Runs full robot stack
- **WSL (Dev PC)**: Runs gamepad controller node
- **Network**: Both must be on same network with matching `ROS_DOMAIN_ID=0`

---

## Prerequisites

### Raspberry Pi
- ROS2 Humble already installed
- Robot stack built and working
- Connected to network (WiFi or Ethernet)

### Windows (WSL)
- WSL2 with Ubuntu 22.04 (or compatible)
- ROS2 Humble installed
- `inputs` library installed
- Gamepad connected via USB

---

## Network Setup (One-Time)

### 1. Find Your Raspberry Pi IP Address

SSH into the Pi and find its IP:

```bash
# On Pi
hostname -I
# Example output: 192.168.1.100
```

### 2. Ensure Both on Same Network

- **Pi**: WiFi or wired Ethernet
- **Windows PC**: WiFi or wired Ethernet
- Both should be able to ping each other

Test connectivity:
```bash
# From WSL
ping 192.168.1.100  # Replace with your Pi's IP
```

### 3. Update /etc/hosts (Optional but Recommended)

Edit `/etc/hosts` on both machines to use hostnames:

**On Pi:**
```bash
sudo nano /etc/hosts
# Add your WSL machine (if you know its IP, e.g., 192.168.1.50):
# 192.168.1.50  dev-pc
```

**On WSL:**
```bash
sudo nano /etc/hosts
# Add your Pi:
192.168.1.100  robot-pi
```

---

## Step-by-Step Launch Instructions

### Phase 1: Rebuild the Workspace (Do This Once)

On **both Pi and WSL**, rebuild the workspace with the new gamepad_controller package:

**On Pi:**
```bash
cd ~/ros2_ws  # Or wherever your uofm-competition-bot is
colcon build
source install/setup.bash
```

**On WSL:**
```bash
cd ~/ros2_ws
colcon build
source install/setup.bash
```

---

### Phase 2: Launch on Raspberry Pi

Connect to your Pi via SSH:

```bash
ssh pi@192.168.1.100
# or: ssh pi@robot-pi
```

Start the robot bringup stack (WITHOUT gamepad, the robot will wait for commands):

```bash
# Set ROS_DOMAIN_ID so remote gamepad can discover it
export ROS_DOMAIN_ID=0
source ~/ros2_ws/install/setup.bash

# Option A: Full stack with navigation
ros2 launch robot_bringup robot.launch.py

# Option B: Without navigation (faster startup for testing)
ros2 launch robot_bringup robot.launch.py use_nav:=false
```

**Expected Output:**
```
[INFO] [robot_state_publisher]: ... Publishing transforms
[INFO] [tb6612_motor_driver_node]: TB6612 drivers initialized
[INFO] [effectors_node]: Effectors online
```

**Leave this terminal open** — the Pi is now running and waiting for `/cmd_vel` commands.

---

### Phase 3: Launch on WSL (Dev PC)

**Open a NEW terminal on your Windows PC** (NOT the Pi terminal), then:

```bash
# Open WSL
wsl

# Inside WSL:
cd ~/ros2_ws
export ROS_DOMAIN_ID=0
source install/setup.bash

# Install inputs library if not already done
pip install inputs

# Option A: Just the gamepad controller (standalone)
ros2 run gamepad_controller gamepad_controller

# Option B: Full bringup with gamepad (if testing full stack)
ros2 launch robot_bringup robot_with_gamepad.launch.py use_nav:=false
```

**Expected Output:**
```
[INFO] Gamepad controller ready. Publishing to '/cmd_vel'
  Max linear speed: 1.0 m/s
  Max angular speed: 2.0 rad/s
  Deadzone: 0.1
Use: Left stick Y for speed, Right stick X for turn
     Press B to emergency stop, A to toggle enable
```

---

### Phase 4: Verify Network Discovery

In a **third terminal on WSL**, check that the gamepad can see the robot's topics:

```bash
wsl
export ROS_DOMAIN_ID=0
source ~/ros2_ws/install/setup.bash

# Should list gamepad_controller and robot nodes
ros2 node list

# Should show /cmd_vel and other topics
ros2 topic list

# Watch the gamepad commands being published
ros2 topic echo /cmd_vel
```

---

## Testing the Connection

### Without Moving the Robot

1. **Pi running**: `robot.launch.py` started ✓
2. **WSL running**: `gamepad_controller` started ✓
3. **Check topic echo (3rd WSL terminal)**: `ros2 topic echo /cmd_vel`
4. **Move gamepad left stick**: You should see `linear.x` values change
5. **Move gamepad right stick**: You should see `angular.z` values change

If topics are publishing but robot doesn't move, check:
- Motor driver is enabled (STBY pin HIGH)
- Power is connected to motors
- TB6612FNG drivers are working (test with `quick_motor_test.py`)

---

## Full Integration (Robot + Gamepad)

Once you've tested separately, use the unified launch on **Pi**:

```bash
export ROS_DOMAIN_ID=0
source ~/ros2_ws/install/setup.bash

# Run full robot with gamepad listening
ros2 launch robot_bringup robot_with_gamepad.launch.py use_nav:=false max_linear_speed:=0.8
```

This assumes your gamepad node is running on a remote machine (WSL or another PC) and will automatically discover the Pi's `/cmd_vel` topic.

---

## Troubleshooting

### "No nodes discovered" / Topics not appearing

1. **Check ROS_DOMAIN_ID**:
   ```bash
   echo $ROS_DOMAIN_ID  # Should be 0 on both Pi and WSL
   ```

2. **Check networking**:
   ```bash
   ping robot-pi  # From WSL, should succeed
   ros2 daemon stop && ros2 daemon start  # Restart discovery
   ```

3. **Check firewall**:
   - Windows Firewall may block ROS2 DDS discovery
   - Ensure both machines are on same subnet
   - Temporarily disable Windows Firewall for testing:
     ```powershell
     # Run as Administrator in PowerShell
     Set-NetFirewallProfile -Profile Domain,Public,Private -Enabled $false
     ```

### Gamepad not detected

1. **Verify gamepad is connected**:
   ```bash
   lsusb  # In WSL, should show your gamepad
   ```

2. **Reinstall inputs library**:
   ```bash
   pip install --upgrade inputs
   ```

3. **Check inputs can see gamepad**:
   ```python
   python3 -c "from inputs import get_gamepad; print(list(get_gamepad()))"
   ```

### Robot not moving when gamepad sends commands

1. **Check motors are powered**: LED on TB6612 should be ON
2. **Test motors directly**:
   ```bash
   python3 ~/ros2_ws/src/uofm-competition-bot/quick_motor_test.py
   ```
3. **Check /cmd_vel is being published**:
   ```bash
   ros2 topic echo /cmd_vel
   ```
4. **Verify motor driver node is running**:
   ```bash
   ros2 node list  # Should show tb6612_motor_driver_node
   ```

---

## Advanced Options

### Adjust Gamepad Sensitivity

When launching, override the speed parameters:

```bash
# On WSL:
ros2 run gamepad_controller gamepad_controller --ros-args -p max_linear_speed:=0.5 -p max_angular_speed:=1.0
```

Or in a launch file:
```bash
ros2 launch robot_bringup robot_with_gamepad.launch.py max_linear_speed:=0.5 max_angular_speed:=1.0
```

### Running Gamepad on Pi Itself (Optional)

If your Pi has a USB gamepad, you can run gamepad_controller directly on the Pi instead of WSL:

```bash
# On Pi:
export ROS_DOMAIN_ID=0
source ~/ros2_ws/install/setup.bash
ros2 run gamepad_controller gamepad_controller
```

This is simpler for testing but uses Pi resources.

---

## Shutdown Procedure

1. **Release joystick** (A button to disable)
2. **In WSL terminal**: `Ctrl+C` to stop gamepad_controller
3. **In Pi terminal**: `Ctrl+C` to stop robot bringup
4. **Verify motors stop** immediately

---

## Next Steps

- Integrate gamepad with navigation (twist multiplexer for dual-mode)
- Add telemetry feedback to gamepad
- Implement dead-man safety switch
- Test in competition environment

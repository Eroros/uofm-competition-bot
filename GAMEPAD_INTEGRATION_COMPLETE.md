# Gamepad Controller - Integration Complete ✓

## Summary of Changes

The gamepad controller has been **integrated into the main robot workspace**.

### Files Created/Modified

**New Package:**
- `src/gamepad_controller/` — Complete ROS2 node for reading gamepad input
  - `gamepad_controller_node.py` — Main node (~250 lines)
  - `launch/gamepad_controller.launch.py` — Launch configuration
  - `package.xml`, `setup.py` — ROS2 metadata

**New Launch File:**
- `src/robot_bringup/launch/robot_with_gamepad.launch.py` — Master launch including gamepad

**Updated Files:**
- `src/robot_bringup/package.xml` — Added gamepad_controller dependency
- `README.md` — Added gamepad section with quick start

**Documentation:**
- `GAMEPAD_LAUNCH_GUIDE.md` — **Full detailed instructions** (read this)
- `GAMEPAD_QUICK_START.md` — Quick reference cheat sheet
- `INTEGRATION_STEPS.md` — How integration was done (for reference)

---

## How It Works

1. **Raspberry Pi** runs: `robot.launch.py` (motors, sensors)
2. **Windows WSL** runs: `gamepad_controller` node
3. **Network**: Both discover each other via ROS2 DDS (same ROS_DOMAIN_ID)
4. **Control**: Gamepad publishes to `/cmd_vel` → motor driver receives and drives wheels

---

## Quick Start (After Rebuild)

### Step 1: Rebuild Workspace (do once)

**On Pi:**
```bash
cd ~/ros2_ws
colcon build
source install/setup.bash
```

**On WSL (Windows):**
```bash
cd ~/ros2_ws
colcon build
source install/setup.bash
```

### Step 2: Launch on Raspberry Pi

```bash
ssh pi@192.168.1.100  # (replace with your Pi's IP)

# Inside Pi:
export ROS_DOMAIN_ID=0
source ~/ros2_ws/install/setup.bash
ros2 launch robot_bringup robot.launch.py use_nav:=false
```

Leave this terminal open. Robot is now waiting for `/cmd_vel` commands.

### Step 3: Launch on Windows WSL (New Terminal)

```bash
# Open WSL from Windows
wsl

# Inside WSL:
export ROS_DOMAIN_ID=0
source ~/ros2_ws/install/setup.bash
pip install inputs  # one-time install
ros2 run gamepad_controller gamepad_controller
```

**You should now see:**
```
[INFO] Gamepad controller ready. Publishing to '/cmd_vel'
  Max linear speed: 1.0 m/s
  Max angular speed: 2.0 rad/s
...
Use: Left stick Y for speed, Right stick X for turn
```

### Step 4: Test

- **Move gamepad left stick**: Robot moves forward/backward
- **Move gamepad right stick**: Robot turns left/right
- **Press A button**: Toggle enable/disable (wheels lock when disabled)
- **Press B button**: Emergency stop

---

## Full Launch Commands

### Option A: Just Motors + Gamepad (Fastest for Testing)

**Pi:**
```bash
export ROS_DOMAIN_ID=0 && source ~/ros2_ws/install/setup.bash && ros2 launch robot_bringup robot.launch.py use_nav:=false
```

**WSL:**
```bash
wsl && export ROS_DOMAIN_ID=0 && source ~/ros2_ws/install/setup.bash && pip install -q inputs && ros2 run gamepad_controller gamepad_controller
```

### Option B: Full Stack with Navigation

**Pi:**
```bash
export ROS_DOMAIN_ID=0 && source ~/ros2_ws/install/setup.bash && ros2 launch robot_bringup robot_with_gamepad.launch.py
```

(This includes motors, sensors, nav2, AND gamepad listening)

**WSL:**
```bash
# Not needed if using robot_with_gamepad.launch.py
# It will automatically find the gamepad node on the network
# OR run standalone gamepad node for testing
wsl && export ROS_DOMAIN_ID=0 && source ~/ros2_ws/install/setup.bash && ros2 run gamepad_controller gamepad_controller
```

---

## Gamepad Controls

| Input | Action |
|-------|--------|
| **Left Stick ↕️** | Forward (up) / Backward (down) |
| **Right Stick ↔️** | Turn left (left) / Turn right (right) |
| **A Button** | Toggle enable/disable |
| **B Button** | Emergency stop |

---

## Troubleshooting

### Topics not discovered

1. **Check ROS_DOMAIN_ID on both machines:**
   ```bash
   echo $ROS_DOMAIN_ID  # Should show 0
   ```

2. **Verify network connectivity:**
   ```bash
   ping robot-pi  # From WSL, should work
   ```

3. **Restart ROS2 daemon:**
   ```bash
   ros2 daemon stop && ros2 daemon start
   ```

4. **Check Windows Firewall:**
   - May block ROS2 discovery
   - Temporarily disable for testing (as admin in PowerShell):
     ```powershell
     Set-NetFirewallProfile -Profile Domain,Public,Private -Enabled $false
     ```

### Gamepad not detected

```bash
# Check gamepad is connected
lsusb  # Should show your gamepad

# Verify inputs library can read it
python3 -c "from inputs import get_gamepad; print('OK')"
```

### Robot doesn't move

1. **Check `/cmd_vel` is publishing:**
   ```bash
   ros2 topic echo /cmd_vel  # In 3rd terminal
   ```

2. **Verify motor driver is online:**
   ```bash
   ros2 node list  # Should show tb6612_motor_driver_node
   ```

3. **Test motors directly:**
   ```bash
   python3 ~/ros2_ws/src/uofm-competition-bot/quick_motor_test.py
   ```

---

## For More Details

- **Full instructions:** Read [GAMEPAD_LAUNCH_GUIDE.md](GAMEPAD_LAUNCH_GUIDE.md)
- **Cheat sheet:** [GAMEPAD_QUICK_START.md](GAMEPAD_QUICK_START.md)
- **How it was integrated:** [INTEGRATION_STEPS.md](../INTEGRATION_STEPS.md)

---

## Next Steps

- [ ] Rebuild workspace on both Pi and WSL: `colcon build`
- [ ] Set up network (same WiFi, matching `ROS_DOMAIN_ID=0`)
- [ ] Follow Quick Start above to test
- [ ] Adjust gamepad sensitivity in launch file if needed:
  ```bash
  ros2 launch robot_bringup robot_with_gamepad.launch.py max_linear_speed:=0.8 max_angular_speed:=1.5
  ```

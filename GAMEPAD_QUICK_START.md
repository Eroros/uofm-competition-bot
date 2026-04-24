# Quick Launch Cheat Sheet

## One-Line Quick Start (After Network Setup)

### Terminal 1: On Raspberry Pi (SSH)

```bash
export ROS_DOMAIN_ID=0 && source ~/ros2_ws/install/setup.bash && ros2 launch robot_bringup robot.launch.py use_nav:=false
```

### Terminal 2: On WSL (Windows)

```bash
wsl
export ROS_DOMAIN_ID=0 && source ~/ros2_ws/install/setup.bash && pip install -q inputs && ros2 run gamepad_controller gamepad_controller
```

---

## What Each Command Does

| Machine | Command | Purpose |
|---------|---------|---------|
| **Pi** | `export ROS_DOMAIN_ID=0` | Set network ID for discovery |
| | `source ~/ros2_ws/install/setup.bash` | Load ROS2 environment |
| | `ros2 launch robot.launch.py use_nav:=false` | Start motors + drivers (skip navigation for speed) |
| **WSL** | `wsl` | Open Windows Subsystem for Linux |
| | `export ROS_DOMAIN_ID=0` | Match Pi's network ID |
| | `source ~/ros2_ws/install/setup.bash` | Load ROS2 environment |
| | `pip install -q inputs` | Install gamepad library (quiet mode) |
| | `ros2 run gamepad_controller gamepad_controller` | Start reading gamepad, send to robot |

---

## Expected Output

### Pi Terminal (Should See):
```
[robot_state_publisher]: Publishing transforms...
[tb6612_motor_driver_node]: Motor drivers initialized
[effectors_node]: Effectors online
```

### WSL Terminal (Should See):
```
[INFO] Gamepad controller ready. Publishing to '/cmd_vel'
  Max linear speed: 1.0 m/s
  Max angular speed: 2.0 rad/s
Use: Left stick Y for speed, Right stick X for turn
     Press B to emergency stop, A to toggle enable
```

---

## Gamepad Controls

| Control | Action |
|---------|--------|
| **Left Stick ⬆️⬇️** | Forward / Backward |
| **Right Stick ⬅️➡️** | Turn Left / Right |
| **A Button** | Toggle Enable (disable = wheels locked) |
| **B Button** | Emergency Stop (hard disable) |

---

## If It Doesn't Work

1. **Verify IP connectivity**: `ping robot-pi` (from WSL)
2. **Check ROS_DOMAIN_ID**: `echo $ROS_DOMAIN_ID` (should be 0 on both)
3. **Verify topics**: `ros2 topic list` (should show `/cmd_vel` and others)
4. **Echo gamepad commands**: `ros2 topic echo /cmd_vel` (in 3rd terminal)
5. **Check firewall**: Disable Windows Firewall for testing

See [GAMEPAD_LAUNCH_GUIDE.md](GAMEPAD_LAUNCH_GUIDE.md) for full troubleshooting.

---

## Cleanup

Stop everything with `Ctrl+C` in both terminals. Motors should stop immediately.

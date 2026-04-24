#!/usr/bin/env python3
"""
gamepad_controller_node.py
~~~~~~~~~~~~~~~~~~~~~~~~~~
ROS2 node for reading XInput/gamepad input and publishing Twist commands.

Converts gamepad analog sticks to velocity commands for skid-steer robot:
  - Left stick Y-axis  → linear.x (forward/backward)
  - Right stick X-axis → angular.z (turn)

Buttons (customizable):
  - A (button_a)     → Toggle enable/disable
  - B (button_b)     → Emergency stop (zero velocity)

Dependencies:
  - inputs (pip install inputs)
  - rclpy
  - geometry_msgs

Usage:
  ros2 run gamepad_controller gamepad_controller

Parameters (configurable via launch file):
  - cmd_vel_topic (str):      Topic to publish Twist to [default: /cmd_vel]
  - max_linear_speed (float): Max forward speed m/s [default: 1.0]
  - max_angular_speed (float): Max turn rate rad/s [default: 2.0]
  - deadzone (float):          Analog stick deadzone 0-1 [default: 0.1]
"""

import math
import threading
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist

try:
    from inputs import get_gamepad
    INPUTS_AVAILABLE = True
except ImportError:
    INPUTS_AVAILABLE = False
    print("WARNING: 'inputs' library not found. Install with: pip install inputs")


# ═══════════════════════════════════════════════════════════════════════
# Gamepad Input Reader (background thread)
# ═══════════════════════════════════════════════════════════════════════

class GamepadReader:
    """Thread-safe gamepad state tracker."""
    
    def __init__(self, deadzone=0.1):
        self.deadzone = deadzone
        self.state = {
            'left_stick_x': 0.0,      # Normalized -1 to 1
            'left_stick_y': 0.0,      # Normalized -1 to 1
            'right_stick_x': 0.0,     # Normalized -1 to 1
            'right_stick_y': 0.0,     # Normalized -1 to 1
            'left_trigger': 0.0,      # Normalized 0 to 1
            'right_trigger': 0.0,     # Normalized 0 to 1
            'button_a': False,
            'button_b': False,
            'button_x': False,
            'button_y': False,
            'dpad_x': 0,              # -1, 0, 1
            'dpad_y': 0,              # -1, 0, 1
        }
        self.lock = threading.Lock()
        self.active = True
        
    def apply_deadzone(self, value):
        """Apply deadzone to analog stick input."""
        if abs(value) < self.deadzone:
            return 0.0
        # Remap to remove the deadzone
        sign = 1 if value > 0 else -1
        normalized = (abs(value) - self.deadzone) / (1.0 - self.deadzone)
        return sign * min(normalized, 1.0)
    
    def update_from_event(self, event):
        """Update state from inputs library event."""
        with self.lock:
            # Analog sticks (signed: -32768 to 32767)
            if event.ev_type == 'Absolute':
                # Normalize to -1 to 1
                norm_val = event.state / 32768.0
                
                if event.code == 'ABS_X':
                    self.state['left_stick_x'] = self.apply_deadzone(norm_val)
                elif event.code == 'ABS_Y':
                    # Invert Y (down is negative in inputs, but we want up=positive)
                    self.state['left_stick_y'] = self.apply_deadzone(-norm_val)
                elif event.code == 'ABS_RX':
                    self.state['right_stick_x'] = self.apply_deadzone(norm_val)
                elif event.code == 'ABS_RY':
                    self.state['right_stick_y'] = self.apply_deadzone(-norm_val)
                elif event.code == 'ABS_Z':
                    self.state['left_trigger'] = (norm_val + 1) / 2.0  # Convert to 0-1
                elif event.code == 'ABS_RZ':
                    self.state['right_trigger'] = (norm_val + 1) / 2.0
                elif event.code == 'ABS_HAT0X':
                    self.state['dpad_x'] = event.state
                elif event.code == 'ABS_HAT0Y':
                    self.state['dpad_y'] = event.state
                    
            # Buttons
            elif event.ev_type == 'Key':
                pressed = event.state == 1
                if event.code == 'BTN_A':
                    self.state['button_a'] = pressed
                elif event.code == 'BTN_B':
                    self.state['button_b'] = pressed
                elif event.code == 'BTN_X':
                    self.state['button_x'] = pressed
                elif event.code == 'BTN_Y':
                    self.state['button_y'] = pressed
    
    def get_state(self):
        """Thread-safe state snapshot."""
        with self.lock:
            return self.state.copy()
    
    def stop(self):
        """Signal reader to stop."""
        self.active = False


def gamepad_input_thread(reader, node):
    """Background thread that reads gamepad events."""
    if not INPUTS_AVAILABLE:
        return
    
    try:
        for event in get_gamepad():
            if not reader.active:
                break
            reader.update_from_event(event)
    except Exception as e:
        node.get_logger().error(f"Gamepad read error: {e}")


# ═══════════════════════════════════════════════════════════════════════
# ROS2 Node
# ═══════════════════════════════════════════════════════════════════════

class GamepadControllerNode(Node):
    """ROS2 node for gamepad → Twist conversion."""
    
    def __init__(self):
        super().__init__('gamepad_controller')
        
        # Declare parameters
        self.declare_parameter('cmd_vel_topic', '/cmd_vel')
        self.declare_parameter('max_linear_speed', 1.0)
        self.declare_parameter('max_angular_speed', 2.0)
        self.declare_parameter('deadzone', 0.1)
        
        # Get parameters
        self.cmd_vel_topic = self.get_parameter('cmd_vel_topic').value
        self.max_linear = self.get_parameter('max_linear_speed').value
        self.max_angular = self.get_parameter('max_angular_speed').value
        deadzone = self.get_parameter('deadzone').value
        
        # Publisher
        self.cmd_vel_pub = self.create_publisher(Twist, self.cmd_vel_topic, 10)
        
        # Gamepad state
        self.gamepad = GamepadReader(deadzone=deadzone)
        self.enabled = True
        
        # Start gamepad input thread
        if INPUTS_AVAILABLE:
            self.reader_thread = threading.Thread(
                target=gamepad_input_thread,
                args=(self.gamepad, self),
                daemon=True
            )
            self.reader_thread.start()
            self.get_logger().info("Gamepad reader thread started")
        else:
            self.get_logger().error("inputs library not available. Cannot read gamepad.")
            return
        
        # Main control loop (50 Hz)
        self.timer = self.create_timer(0.02, self.control_callback)
        
        self.get_logger().info(
            f"Gamepad controller ready. Publishing to '{self.cmd_vel_topic}'\n"
            f"  Max linear speed: {self.max_linear} m/s\n"
            f"  Max angular speed: {self.max_angular} rad/s\n"
            f"  Deadzone: {deadzone}\n"
            f"Use: Left stick Y for speed, Right stick X for turn\n"
            f"     Press B to emergency stop, A to toggle enable"
        )
    
    def control_callback(self):
        """Main control loop: read gamepad, publish Twist."""
        if not INPUTS_AVAILABLE:
            return
        
        state = self.gamepad.get_state()
        
        # Toggle enable on A button
        if state['button_a']:
            self.enabled = not self.enabled
            self.get_logger().info(f"Controller {'ENABLED' if self.enabled else 'DISABLED'}")
        
        # Emergency stop on B button
        if state['button_b']:
            self.enabled = False
            self.get_logger().warn("EMERGENCY STOP")
        
        # Build Twist command
        twist = Twist()
        
        if self.enabled:
            # Left stick Y → linear.x (forward/backward)
            twist.linear.x = state['left_stick_y'] * self.max_linear
            
            # Right stick X → angular.z (turn)
            twist.angular.z = state['right_stick_x'] * self.max_angular
        else:
            twist.linear.x = 0.0
            twist.angular.z = 0.0
        
        self.cmd_vel_pub.publish(twist)


def main(args=None):
    """ROS2 entry point."""
    rclpy.init(args=args)
    try:
        node = GamepadControllerNode()
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        rclpy.shutdown()


if __name__ == '__main__':
    main()

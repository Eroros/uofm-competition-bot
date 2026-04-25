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
import json
import socket
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
        self.declare_parameter('tcp_listen_host', '0.0.0.0')
        self.declare_parameter('tcp_listen_port', 5005)
        self.declare_parameter('use_tcp_input', False)
        
        # Get parameters
        self.cmd_vel_topic = self.get_parameter('cmd_vel_topic').value
        self.max_linear = self.get_parameter('max_linear_speed').value
        self.max_angular = self.get_parameter('max_angular_speed').value
        deadzone = self.get_parameter('deadzone').value
        self.tcp_listen_host = self.get_parameter('tcp_listen_host').value
        self.tcp_listen_port = int(self.get_parameter('tcp_listen_port').value)
        self.use_tcp_input = bool(self.get_parameter('use_tcp_input').value)
        
        # Publisher
        self.cmd_vel_pub = self.create_publisher(Twist, self.cmd_vel_topic, 10)
        
        # Gamepad state
        self.gamepad = GamepadReader(deadzone=deadzone)
        self.enabled = True
        self._last_tcp_cmd = None
        
        if self.use_tcp_input:
            self.tcp_thread = threading.Thread(
                target=self.tcp_input_thread,
                daemon=True,
            )
            self.tcp_thread.start()
            self.get_logger().info(
                f"TCP input listener started on {self.tcp_listen_host}:{self.tcp_listen_port}"
            )
        elif INPUTS_AVAILABLE:
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

    def tcp_input_thread(self):
        """Listen for newline-delimited JSON commands and publish Twist."""
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server.bind((self.tcp_listen_host, self.tcp_listen_port))
        server.listen(1)
        server.settimeout(1.0)

        self.get_logger().info("Waiting for TCP gamepad stream connection...")
        client = None
        try:
            while rclpy.ok():
                if client is None:
                    try:
                        client, addr = server.accept()
                        client.settimeout(1.0)
                        self.get_logger().info(f"TCP client connected from {addr[0]}:{addr[1]}")
                    except socket.timeout:
                        continue

                try:
                    data = client.recv(1024)
                    if not data:
                        self.get_logger().info("TCP client disconnected")
                        client.close()
                        client = None
                        continue

                    for raw_line in data.decode("utf-8", errors="ignore").splitlines():
                        raw_line = raw_line.strip()
                        if not raw_line:
                            continue
                        self.handle_tcp_command(raw_line)
                except socket.timeout:
                    continue
                except OSError as exc:
                    self.get_logger().warn(f"TCP receive error: {exc}")
                    if client is not None:
                        client.close()
                    client = None
        finally:
            if client is not None:
                client.close()
            server.close()

    def handle_tcp_command(self, raw_line: str):
        """Parse a JSON command payload and publish Twist."""
        try:
            msg = json.loads(raw_line)
            if not isinstance(msg, dict):
                raise ValueError("payload must be a JSON object")
        except Exception as exc:
            self.get_logger().warn(f"Bad TCP command ignored: {exc}")
            return

        linear = float(msg.get("linear", 0.0))
        angular = float(msg.get("angular", 0.0))

        twist = Twist()
        twist.linear.x = linear
        twist.angular.z = angular
        self.cmd_vel_pub.publish(twist)
        self._last_tcp_cmd = raw_line
        self.get_logger().info(f"TCP cmd_vel published: {raw_line}")
    
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

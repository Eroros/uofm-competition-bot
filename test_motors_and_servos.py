#!/usr/bin/env python3
"""
test_motors_and_servos.py
~~~~~~~~~~~~~~~~~~~~~~~~~
Standalone test script (no ROS) for all motors and servos on the robot.
Tests each motor and servo sequentially to verify hardware connections.

GPIO pin map (BCM numbering) — from pinout.txt (physical pins 1-40):
  Front TB6612FNG (motors FL & FR):
    FL: PWM=12 (pin 32), IN1=5 (pin 29), IN2=6 (pin 31)
    FR: PWM=13 (pin 33), IN1=19 (pin 35), IN2=26 (pin 37) | STBY=21 (pin 40)
  
  Rear TB6612FNG (motors RL & RR):
    RL: PWM=18 (pin 12), IN1=17 (pin 11), IN2=27 (pin 13)
    RR: PWM=25 (pin 22), IN1=22 (pin 15), IN2=24 (pin 18) | STBY=20 (pin 38)
  
  DSServos:
    Paddle Left:  GPIO 23 (pin 16)
    Paddle Right: GPIO 16 (pin 36)
    Crank:        GPIO 7 (pin 26)

Each motor is tested forward → reverse → stop.
Each servo sweeps from 0° → 90° → 180° → 90° → 0°.
"""

import time
import sys

# Try to import RPi.GPIO; fall back to stub mode if not on Pi
try:
    import RPi.GPIO as GPIO
    HW_AVAILABLE = True
    print("[INFO] RPi.GPIO available — hardware mode enabled")
except ImportError:
    HW_AVAILABLE = False
    print("[WARNING] RPi.GPIO not available — stub mode (no actual GPIO control)")


# ═══════════════════════════════════════════════════════════════════════════
# Motor Driver Classes
# ═══════════════════════════════════════════════════════════════════════════

class TB6612Driver:
    """Control one TB6612FNG chip (channels A and B)."""
    
    def __init__(self, name, pwm_a, ain1, ain2, pwm_b, bin1, bin2, stby, pwm_freq=1000):
        self.name = name
        self.pins = {
            "pwm_a": pwm_a, "ain1": ain1, "ain2": ain2,
            "pwm_b": pwm_b, "bin1": bin1, "bin2": bin2,
            "stby":  stby,
        }
        self.pwm_freq = pwm_freq
        self._pwm_a = None
        self._pwm_b = None
        self._enabled = False
    
    def setup(self):
        """Initialize GPIO pins."""
        if not HW_AVAILABLE:
            print(f"  [STUB] {self.name}: GPIO setup (stub)")
            return
        
        try:
            for pin in self.pins.values():
                GPIO.setup(pin, GPIO.OUT)
            self._pwm_a = GPIO.PWM(self.pins["pwm_a"], self.pwm_freq)
            self._pwm_b = GPIO.PWM(self.pins["pwm_b"], self.pwm_freq)
            self._pwm_a.start(0)
            self._pwm_b.start(0)
            GPIO.output(self.pins["stby"], GPIO.HIGH)  # Enable chip
            self._enabled = True
            print(f"  [OK] {self.name}: GPIO initialized")
        except Exception as e:
            print(f"  [ERROR] {self.name}: {e}")
    
    def set_speed(self, channel: str, speed: float):
        """
        Set motor speed and direction.
        Args:
            channel: "A" or "B"
            speed: -1.0 (full reverse) → 0.0 (stop) → +1.0 (full forward)
        """
        speed = max(-1.0, min(1.0, speed))
        duty = abs(speed) * 100.0
        forward = speed >= 0.0
        
        if channel == "A":
            in1, in2, pwm_obj = self.pins["ain1"], self.pins["ain2"], self._pwm_a
        else:
            in1, in2, pwm_obj = self.pins["bin1"], self.pins["bin2"], self._pwm_b
        
        if not HW_AVAILABLE:
            direction = "FWD" if forward else "REV" if speed < 0 else "STOP"
            print(f"    [STUB] Channel {channel}: {direction} (duty={duty:.1f}%)")
            return
        
        try:
            if duty < 1.0:
                GPIO.output(in1, GPIO.LOW)
                GPIO.output(in2, GPIO.LOW)
                pwm_obj.ChangeDutyCycle(0)
            elif forward:
                GPIO.output(in1, GPIO.HIGH)
                GPIO.output(in2, GPIO.LOW)
                pwm_obj.ChangeDutyCycle(duty)
            else:
                GPIO.output(in1, GPIO.LOW)
                GPIO.output(in2, GPIO.HIGH)
                pwm_obj.ChangeDutyCycle(duty)
        except Exception as e:
            print(f"    [ERROR] Channel {channel}: {e}")
    
    def stop(self):
        """Stop both channels."""
        self.set_speed("A", 0.0)
        self.set_speed("B", 0.0)
    
    def cleanup(self):
        if self._pwm_a:
            self._pwm_a.stop()
        if self._pwm_b:
            self._pwm_b.stop()
        if HW_AVAILABLE:
            GPIO.output(self.pins["stby"], GPIO.LOW)


# ═══════════════════════════════════════════════════════════════════════════
# Servo Controller Class
# ═══════════════════════════════════════════════════════════════════════════

class DSServoController:
    """Control a single DSServo via PWM."""
    
    SERVO_FREQ = 50  # Hz
    
    def __init__(self, name, pin):
        self.name = name
        self.pin = pin
        self._pwm = None
    
    def setup(self):
        """Initialize GPIO and PWM for servo."""
        if not HW_AVAILABLE:
            print(f"  [STUB] {self.name}: GPIO setup (stub)")
            return
        
        try:
            GPIO.setup(self.pin, GPIO.OUT)
            self._pwm = GPIO.PWM(self.pin, self.SERVO_FREQ)
            self._pwm.start(self._angle_to_duty(90.0))  # Start at neutral
            print(f"  [OK] {self.name}: GPIO initialized (pin {self.pin})")
        except Exception as e:
            print(f"  [ERROR] {self.name}: {e}")
    
    @staticmethod
    def _angle_to_duty(angle_deg: float) -> float:
        """Convert servo angle (0–180°) to PWM duty cycle (0–100)."""
        # DSServo: 0° = 0.5 ms, 180° = 2.5 ms, period = 20 ms
        pulse_ms = 0.5 + (angle_deg / 180.0) * 2.0
        return (pulse_ms / 20.0) * 100.0
    
    def set_angle(self, angle_deg: float):
        """Move servo to angle."""
        angle_deg = max(0.0, min(180.0, angle_deg))
        
        if not HW_AVAILABLE:
            print(f"    [STUB] {self.name}: angle={angle_deg:.1f}°")
            return
        
        try:
            duty = self._angle_to_duty(angle_deg)
            self._pwm.ChangeDutyCycle(duty)
        except Exception as e:
            print(f"    [ERROR] {self.name}: {e}")
    
    def cleanup(self):
        if self._pwm:
            self._pwm.stop()


# ═══════════════════════════════════════════════════════════════════════════
# Test Routines
# ═══════════════════════════════════════════════════════════════════════════

def test_motor(driver: TB6612Driver, channel: str, channel_name: str, duration: float = 2.0):
    """Test one motor channel: forward → reverse → stop."""
    print(f"\n  Testing {driver.name} - Channel {channel} ({channel_name})")
    
    # Forward
    print(f"    Forward (75% duty) for {duration}s...")
    driver.set_speed(channel, 0.75)
    time.sleep(duration)
    
    # Reverse
    print(f"    Reverse (75% duty) for {duration}s...")
    driver.set_speed(channel, -0.75)
    time.sleep(duration)
    
    # Stop
    print(f"    Stop...")
    driver.set_speed(channel, 0.0)
    time.sleep(0.5)


def test_servo(servo: DSServoController, duration_per_pos: float = 1.0):
    """Test servo: sweep 0° → 90° → 180° → 90° → 0°."""
    print(f"\n  Testing {servo.name}")
    
    angles = [0, 90, 180, 90, 0]
    for angle in angles:
        print(f"    Moving to {angle}°...")
        servo.set_angle(angle)
        time.sleep(duration_per_pos)
    
    # Return to neutral
    servo.set_angle(90.0)


# ═══════════════════════════════════════════════════════════════════════════
# Main Test Sequence
# ═══════════════════════════════════════════════════════════════════════════

def main():
    """Run complete motor and servo test sequence."""
    
    print("\n" + "="*70)
    print("ROBOT MOTOR & SERVO TEST SCRIPT")
    print("="*70)
    print("\nThis script will test:")
    print("  • Front-Left (FL) motor")
    print("  • Front-Right (FR) motor")
    print("  • Rear-Left (RL) motor")
    print("  • Rear-Right (RR) motor")
    print("  • Paddle Left servo")
    print("  • Paddle Right servo")
    print("  • Crank servo")
    print("\n" + "-"*70)
    
    # Initialize GPIO
    if HW_AVAILABLE:
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        print("[INFO] GPIO mode set to BCM")
    
    try:
        # ─── Create driver instances ───────────────────────────────────────
        print("\n[STEP 1] Initializing motor drivers...")
        front_driver = TB6612Driver(
            "Front TB6612FNG",
            pwm_a=12, ain1=5, ain2=6,    # Front-Left
            pwm_b=13, bin1=19, bin2=26,  # Front-Right
            stby=21
        )
        rear_driver = TB6612Driver(
            "Rear TB6612FNG",
            pwm_a=18, ain1=17, ain2=27,  # Rear-Left
            pwm_b=25, bin1=22, bin2=24,  # Rear-Right
            stby=20
        )
        
        front_driver.setup()
        rear_driver.setup()
        
        # ─── Create servo instances ────────────────────────────────────────
        print("\n[STEP 2] Initializing servos...")
        paddle_left = DSServoController("Paddle Left", pin=23)
        paddle_right = DSServoController("Paddle Right", pin=16)
        crank = DSServoController("Crank", pin=7)
        
        paddle_left.setup()
        paddle_right.setup()
        crank.setup()
        
        # ─── Test motors sequentially ──────────────────────────────────────
        print("\n[STEP 3] Testing motors...")
        print("-" * 70)
        
        test_motor(front_driver, "A", "Front-Left", duration=2.0)
        test_motor(front_driver, "B", "Front-Right", duration=2.0)
        test_motor(rear_driver, "A", "Rear-Left", duration=2.0)
        test_motor(rear_driver, "B", "Rear-Right", duration=2.0)
        
        # Stop all motors
        print("\n  Stopping all motors...")
        front_driver.stop()
        rear_driver.stop()
        time.sleep(1.0)
        
        # ─── Test servos sequentially ──────────────────────────────────────
        print("\n[STEP 4] Testing servos...")
        print("-" * 70)
        
        test_servo(paddle_left, duration_per_pos=0.8)
        test_servo(paddle_right, duration_per_pos=0.8)
        test_servo(crank, duration_per_pos=1.0)
        
        # ─── Cleanup ───────────────────────────────────────────────────────
        print("\n[STEP 5] Cleanup...")
        print("-" * 70)
        
        front_driver.stop()
        rear_driver.stop()
        paddle_left.set_angle(90.0)
        paddle_right.set_angle(90.0)
        crank.set_angle(0.0)
        
        time.sleep(0.5)
        front_driver.cleanup()
        rear_driver.cleanup()
        paddle_left.cleanup()
        paddle_right.cleanup()
        crank.cleanup()
        
        if HW_AVAILABLE:
            GPIO.cleanup()
        
        print("\n" + "="*70)
        print("TEST COMPLETE")
        print("="*70)
        print("\n✓ All motors and servos tested successfully!")
        print("  If you did not see any motor/servo movement, check:")
        print("  1. Power connections to TB6612 and servo boards")
        print("  2. GPIO pin connections match the hardcoded values")
        print("  3. Motor/servo power and signal wiring")
        print("  4. No Python errors above\n")
        
    except KeyboardInterrupt:
        print("\n\n[INTERRUPTED] Stopping all motors and servos...")
        if HW_AVAILABLE:
            front_driver.stop()
            rear_driver.stop()
            paddle_left.set_angle(90.0)
            paddle_right.set_angle(90.0)
            crank.set_angle(0.0)
            GPIO.cleanup()
        sys.exit(1)
    except Exception as e:
        print(f"\n\n[ERROR] {e}")
        if HW_AVAILABLE:
            try:
                GPIO.cleanup()
            except:
                pass
        sys.exit(1)


if __name__ == "__main__":
    main()

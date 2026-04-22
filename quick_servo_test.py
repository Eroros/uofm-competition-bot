#!/usr/bin/env python3
"""
quick_servo_test.py
~~~~~~~~~~~~~~~~~~~
Safe servo test — with proper neutral positioning and controlled sweeps.
Prevents servo damage from being stuck at extreme angles.

Usage: sudo python3 quick_servo_test.py
"""

import time
import sys

try:
    import RPi.GPIO as GPIO
    HW = True
except ImportError:
    HW = False
    print("[STUB MODE] RPi.GPIO not available\n")

# ───────────────────────────────────────────────────────────────────
# GPIO pin definitions (from pinout.txt, converted to BCM)
# Physical pins 1-40 on Raspberry Pi
# ───────────────────────────────────────────────────────────────────
PADDLE_LEFT_PIN  = 23   # pin 16
PADDLE_RIGHT_PIN = 16   # pin 36
CRANK_PIN        = 7    # pin 26

PWM_FREQ = 50  # Hz

# Pulse width range (microseconds)
MIN_PULSE = 500   # 0 degrees
MAX_PULSE = 2500  # 180 degrees

def angle_to_duty(angle):
    """Convert angle (0-180°) to duty cycle % for 50Hz PWM."""
    angle = max(0, min(180, angle))  # Clamp to 0-180
    pulse_us = MIN_PULSE + (angle / 180.0) * (MAX_PULSE - MIN_PULSE)
    duty = (pulse_us / 20000.0) * 100.0  # 20000us = 1/50Hz
    # Safety: validate duty cycle is reasonable (2.5-12.5%)
    if duty < 2.0 or duty > 13.0:
        print(f"    [WARNING] Duty cycle {duty:.2f}% out of range!")
    return duty


if HW:
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    
    GPIO.setup(PADDLE_LEFT_PIN, GPIO.OUT)
    GPIO.setup(PADDLE_RIGHT_PIN, GPIO.OUT)
    GPIO.setup(CRANK_PIN, GPIO.OUT)
    
    pwm_pl = GPIO.PWM(PADDLE_LEFT_PIN, PWM_FREQ)
    pwm_pr = GPIO.PWM(PADDLE_RIGHT_PIN, PWM_FREQ)
    pwm_cr = GPIO.PWM(CRANK_PIN, PWM_FREQ)
    
    # Initialize all servos to NEUTRAL (90°) — NOT to 0°
    print("[INFO] Initializing all servos to neutral (90°)")
    pwm_pl.start(angle_to_duty(90.0))
    pwm_pr.start(angle_to_duty(90.0))
    pwm_cr.start(angle_to_duty(90.0))
    time.sleep(1.0)  # Let servos settle to neutral
    
    print("[OK] GPIO initialized\n")


def servo_sweep(name, pwm, start_angle=90, end_angle=45, duration_per_step=0.2):
    """
    Safe servo sweep: start -> end -> start (return to neutral).
    Sweep in small steps to prevent mechanical shock.
    """
    print(f"\nTesting {name} (neutral=90°)")
    
    # Forward sweep
    print(f"  → Sweep {start_angle}° to {end_angle}° ({duration_per_step}s per step)")
    steps = abs(end_angle - start_angle)
    for i in range(steps + 1):
        angle = start_angle + (end_angle - start_angle) * i / max(1, steps)
        if HW:
            pwm.ChangeDutyCycle(angle_to_duty(angle))
        time.sleep(duration_per_step)
    
    # Hold at end
    time.sleep(0.3)
    
    # Return sweep
    print(f"  ← Return {end_angle}° to {start_angle}°")
    for i in range(steps + 1):
        angle = end_angle + (start_angle - end_angle) * i / max(1, steps)
        if HW:
            pwm.ChangeDutyCycle(angle_to_duty(angle))
        time.sleep(duration_per_step)
    
    # Ensure at neutral
    if HW:
        pwm.ChangeDutyCycle(angle_to_duty(90.0))
    time.sleep(0.3)


try:
    print("="*60)
    print("SAFE SERVO TEST")
    print("="*60)
    print("All servos initialize to neutral (90°)")
    print("Servos perform controlled sweeps and return to neutral\n")
    
    # Test paddles with moderate sweep (90° to 60°)
    servo_sweep("Paddle Left",  pwm_pl, start_angle=90, end_angle=60, duration_per_step=0.15)
    servo_sweep("Paddle Right", pwm_pr, start_angle=90, end_angle=60, duration_per_step=0.15)
    
    # Test crank with smaller sweep (90° to 70°) - safer for fragile component
    servo_sweep("Crank", pwm_cr, start_angle=90, end_angle=70, duration_per_step=0.2)
    
    # Final: ensure all at neutral
    print("\n[FINAL] Returning all servos to neutral (90°)")
    if HW:
        pwm_pl.ChangeDutyCycle(angle_to_duty(90.0))
        pwm_pr.ChangeDutyCycle(angle_to_duty(90.0))
        pwm_cr.ChangeDutyCycle(angle_to_duty(90.0))
        time.sleep(0.5)
        
        # Clean stop
        pwm_pl.stop()
        pwm_pr.stop()
        pwm_cr.stop()
        GPIO.cleanup()
    
    print("\n" + "="*60)
    print("✓ Test complete!")
    print("="*60 + "\n")

except KeyboardInterrupt:
    print("\n[INTERRUPTED]")
    if HW:
        try:
            # Return to neutral before cleanup
            print("  Returning servos to neutral...")
            pwm_pl.ChangeDutyCycle(angle_to_duty(90.0))
            pwm_pr.ChangeDutyCycle(angle_to_duty(90.0))
            pwm_cr.ChangeDutyCycle(angle_to_duty(90.0))
            time.sleep(0.5)
            pwm_pl.stop()
            pwm_pr.stop()
            pwm_cr.stop()
            GPIO.cleanup()
        except:
            pass
    sys.exit(1)
except Exception as e:
    print(f"\n[ERROR] {e}")
    if HW:
        try:
            GPIO.cleanup()
        except:
            pass
    sys.exit(1)

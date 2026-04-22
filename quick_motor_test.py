#!/usr/bin/env python3
"""
quick_motor_test.py
~~~~~~~~~~~~~~~~~~~
Minimal motor test — directly based on tb6612_driver.py logic.
Simpler than full test for quick verification.

Usage: sudo python3 quick_motor_test.py
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
# Front motor driver (from pinout.txt)
FL_PWM, FL_IN1, FL_IN2 = 12, 5, 6           # pins 32, 29, 31
FR_PWM, FR_IN1, FR_IN2 = 13, 19, 26        # pins 33, 35, 37
FRONT_STBY = 21                             # pin 40

# Rear motor driver (from pinout.txt)
RL_PWM, RL_IN1, RL_IN2 = 18, 17, 27        # pins 12, 11, 13
RR_PWM, RR_IN1, RR_IN2 = 25, 22, 24        # pins 22, 15, 18
REAR_STBY = 20                              # pin 38

PWM_FREQ = 1000

if HW:
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    
    # Setup pins
    for pin in [FL_IN1, FL_IN2, FR_IN1, FR_IN2, RL_IN1, RL_IN2, RR_IN1, RR_IN2]:
        GPIO.setup(pin, GPIO.OUT)
    for pin in [FL_PWM, FR_PWM, RL_PWM, RR_PWM]:
        GPIO.setup(pin, GPIO.OUT)
    for pin in [FRONT_STBY, REAR_STBY]:
        GPIO.setup(pin, GPIO.OUT)
    
    # Enable drivers
    GPIO.output(FRONT_STBY, GPIO.HIGH)
    GPIO.output(REAR_STBY, GPIO.HIGH)
    
    # Create PWM objects
    pwm_fl = GPIO.PWM(FL_PWM, PWM_FREQ)
    pwm_fr = GPIO.PWM(FR_PWM, PWM_FREQ)
    pwm_rl = GPIO.PWM(RL_PWM, PWM_FREQ)
    pwm_rr = GPIO.PWM(RR_PWM, PWM_FREQ)
    
    for pwm in [pwm_fl, pwm_fr, pwm_rl, pwm_rr]:
        pwm.start(0)
    
    print("[OK] GPIO initialized\n")


def motor_test(name, pwm, in1_pin, in2_pin, duration=2.0):
    """Test one motor: forward -> reverse -> stop."""
    print(f"\nTesting {name}")
    
    # Forward
    print(f"  → Forward for {duration}s")
    if HW:
        GPIO.output(in1_pin, GPIO.HIGH)
        GPIO.output(in2_pin, GPIO.LOW)
        pwm.ChangeDutyCycle(75.0)
    time.sleep(duration)
    
    # Reverse
    print(f"  ← Reverse for {duration}s")
    if HW:
        GPIO.output(in1_pin, GPIO.LOW)
        GPIO.output(in2_pin, GPIO.HIGH)
        pwm.ChangeDutyCycle(75.0)
    time.sleep(duration)
    
    # Stop
    print(f"  ■ Stop")
    if HW:
        GPIO.output(in1_pin, GPIO.LOW)
        GPIO.output(in2_pin, GPIO.LOW)
        pwm.ChangeDutyCycle(0)
    time.sleep(0.5)


try:
    print("="*60)
    print("QUICK MOTOR TEST — Synchronized Wheel Control")
    print("="*60)
    
    # Test front and rear wheels together (in sync)
    print("\n[TEST 1] FRONT & REAR FORWARD (synchronized)")
    print("  → Forward for 2s")
    if HW:
        # Front forward
        GPIO.output(FL_IN1, GPIO.HIGH)
        GPIO.output(FL_IN2, GPIO.LOW)
        GPIO.output(FR_IN1, GPIO.HIGH)
        GPIO.output(FR_IN2, GPIO.LOW)
        pwm_fl.ChangeDutyCycle(75.0)
        pwm_fr.ChangeDutyCycle(75.0)
        
        # Rear forward
        GPIO.output(RL_IN1, GPIO.HIGH)
        GPIO.output(RL_IN2, GPIO.LOW)
        GPIO.output(RR_IN1, GPIO.HIGH)
        GPIO.output(RR_IN2, GPIO.LOW)
        pwm_rl.ChangeDutyCycle(75.0)
        pwm_rr.ChangeDutyCycle(75.0)
    time.sleep(2.0)
    
    print("  ← Reverse for 2s")
    if HW:
        # Front reverse
        GPIO.output(FL_IN1, GPIO.LOW)
        GPIO.output(FL_IN2, GPIO.HIGH)
        GPIO.output(FR_IN1, GPIO.LOW)
        GPIO.output(FR_IN2, GPIO.HIGH)
        pwm_fl.ChangeDutyCycle(75.0)
        pwm_fr.ChangeDutyCycle(75.0)
        
        # Rear reverse
        GPIO.output(RL_IN1, GPIO.LOW)
        GPIO.output(RL_IN2, GPIO.HIGH)
        GPIO.output(RR_IN1, GPIO.LOW)
        GPIO.output(RR_IN2, GPIO.HIGH)
        pwm_rl.ChangeDutyCycle(75.0)
        pwm_rr.ChangeDutyCycle(75.0)
    time.sleep(2.0)
    
    print("  ■ Stop")
    if HW:
        # Stop all
        for in1, in2 in [(FL_IN1, FL_IN2), (FR_IN1, FR_IN2), (RL_IN1, RL_IN2), (RR_IN1, RR_IN2)]:
            GPIO.output(in1, GPIO.LOW)
            GPIO.output(in2, GPIO.LOW)
        for pwm in [pwm_fl, pwm_fr, pwm_rl, pwm_rr]:
            pwm.ChangeDutyCycle(0)
    time.sleep(0.5)
    
    # Test individual motors
    print("\n[TEST 2] INDIVIDUAL MOTORS")
    motor_test("Front-Left",  pwm_fl, FL_IN1, FL_IN2)
    motor_test("Front-Right", pwm_fr, FR_IN1, FR_IN2)
    motor_test("Rear-Left",   pwm_rl, RL_IN1, RL_IN2)
    motor_test("Rear-Right",  pwm_rr, RR_IN1, RR_IN2)
    
    # Stop all
    if HW:
        GPIO.output(FRONT_STBY, GPIO.LOW)
        GPIO.output(REAR_STBY, GPIO.LOW)
        pwm_fl.stop()
        pwm_fr.stop()
        pwm_rl.stop()
        pwm_rr.stop()
        GPIO.cleanup()
    
    print("\n" + "="*60)
    print("✓ Test complete!")
    print("="*60 + "\n")

except KeyboardInterrupt:
    print("\n[INTERRUPTED]")
    if HW:
        GPIO.cleanup()
    sys.exit(1)
except Exception as e:
    print(f"\n[ERROR] {e}")
    if HW:
        try:
            GPIO.cleanup()
        except:
            pass
    sys.exit(1)

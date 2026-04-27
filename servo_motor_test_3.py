#!/usr/bin/env python3
"""
servo_motor_test_3.py

Dead-simple servo test.

Change the values in USER SETTINGS, then run:
  python3 servo_motor_test_3.py

The script sends one servo to one angle, holds briefly, then cleans up.
"""

import time

try:
    import RPi.GPIO as GPIO
    HARDWARE = True
except ImportError:
    HARDWARE = False
    print("[WARNING] RPi.GPIO not available - simulation mode")


# =========================
# USER SETTINGS
# =========================

# BCM GPIO pin number, not physical board pin number.
# Current known paddle pins:
#   Left paddle:  23
#   Right paddle: 16
SERVO_PIN = 23

# Most hobby servos use 50 Hz.
PWM_FREQUENCY_HZ = 50

# Desired servo angle.
# Usually safe range is 0 to 180 degrees.
TARGET_ANGLE_DEGREES = 90

# How long to hold the PWM signal after moving.
HOLD_SECONDS = 1.0


# =========================
# SERVO CALIBRATION
# =========================

# Common servo pulse range:
#   500 us  = about 0 degrees
#   1500 us = about 90 degrees
#   2500 us = about 180 degrees
MIN_PULSE_US = 500
MAX_PULSE_US = 2500


def clamp_angle(angle):
    return max(0.0, min(180.0, float(angle)))


def angle_to_duty_cycle(angle):
    angle = clamp_angle(angle)
    pulse_us = MIN_PULSE_US + (angle / 180.0) * (MAX_PULSE_US - MIN_PULSE_US)
    period_us = 1_000_000.0 / PWM_FREQUENCY_HZ
    return (pulse_us / period_us) * 100.0


def main():
    angle = clamp_angle(TARGET_ANGLE_DEGREES)
    duty_cycle = angle_to_duty_cycle(angle)

    print("\nSimple Servo Test")
    print("=================")
    print(f"Pin:        BCM {SERVO_PIN}")
    print(f"Frequency:  {PWM_FREQUENCY_HZ} Hz")
    print(f"Angle:      {angle:.1f} degrees")
    print(f"Duty cycle: {duty_cycle:.2f}%")

    if not HARDWARE:
        print("\nSimulation mode only. No GPIO signal was sent.")
        return

    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(SERVO_PIN, GPIO.OUT)

    pwm = GPIO.PWM(SERVO_PIN, PWM_FREQUENCY_HZ)
    try:
        pwm.start(duty_cycle)
        time.sleep(HOLD_SECONDS)
    finally:
        pwm.stop()
        GPIO.cleanup()
        print("\nDone. GPIO cleaned up.")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
servo_motor_test_3.py

Small paddle-servo test utility.

Examples:
  python3 servo_motor_test_3.py
  python3 servo_motor_test_3.py -l -5
  python3 servo_motor_test_3.py -r 5
  python3 servo_motor_test_3.py --left closed
  python3 servo_motor_test_3.py --right predeploy
  python3 servo_motor_test_3.py --both neutral
"""

import argparse
import time

try:
    import RPi.GPIO as GPIO
    HARDWARE = True
except ImportError:
    HARDWARE = False
    print("[WARNING] RPi.GPIO not available - simulation mode")


PADDLE_LEFT_PIN = 23
PADDLE_RIGHT_PIN = 16

PWM_FREQ = 50
MIN_PULSE_US = 500
MAX_PULSE_US = 2500

NEUTRAL_ANGLE = 90.0
CLOSED_ANGLE = 0.0
PREDEPLOY_ANGLE = 135.0

STEP_DEG = 5.0
STEP_DELAY = 0.08
SETTLE_DELAY = 0.35

STATES = {
    "neutral": NEUTRAL_ANGLE,
    "open": NEUTRAL_ANGLE,
    "closed": CLOSED_ANGLE,
    "predeploy": PREDEPLOY_ANGLE,
    "pre-deploy": PREDEPLOY_ANGLE,
    "pre_deploy": PREDEPLOY_ANGLE,
}


def clamp_angle(angle):
    return max(0.0, min(180.0, float(angle)))


def physical_angle(side, logical_angle):
    logical_angle = clamp_angle(logical_angle)
    if side == "left":
        return 180.0 - logical_angle
    return logical_angle


def angle_to_duty(angle):
    angle = clamp_angle(angle)
    pulse_us = MIN_PULSE_US + (angle / 180.0) * (MAX_PULSE_US - MIN_PULSE_US)
    return (pulse_us / 20000.0) * 100.0


def setup():
    if not HARDWARE:
        return {}

    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(PADDLE_LEFT_PIN, GPIO.OUT)
    GPIO.setup(PADDLE_RIGHT_PIN, GPIO.OUT)

    pwms = {
        "left": GPIO.PWM(PADDLE_LEFT_PIN, PWM_FREQ),
        "right": GPIO.PWM(PADDLE_RIGHT_PIN, PWM_FREQ),
    }
    for pwm in pwms.values():
        pwm.start(0)
    return pwms


def apply_angle(pwms, side, logical_angle):
    logical_angle = clamp_angle(logical_angle)
    actual_angle = physical_angle(side, logical_angle)
    if HARDWARE:
        pwms[side].ChangeDutyCycle(angle_to_duty(actual_angle))
    print(f"  {side.capitalize():5s}: logical {logical_angle:6.1f} deg -> servo {actual_angle:6.1f} deg")


def move_servo(pwms, current, side, target_angle):
    target_angle = clamp_angle(target_angle)
    start_angle = current[side]
    delta = target_angle - start_angle
    if delta == 0:
        apply_angle(pwms, side, target_angle)
        time.sleep(SETTLE_DELAY)
        return

    step = STEP_DEG if delta > 0 else -STEP_DEG
    angle = start_angle
    while True:
        next_angle = angle + step
        if (step > 0 and next_angle >= target_angle) or (step < 0 and next_angle <= target_angle):
            next_angle = target_angle
        apply_angle(pwms, side, next_angle)
        time.sleep(STEP_DELAY)
        angle = next_angle
        if angle == target_angle:
            break
    time.sleep(SETTLE_DELAY)
    current[side] = target_angle


def move_to_state(pwms, current, side, state):
    state_key = state.lower()
    if state_key not in STATES:
        raise ValueError(f"Unknown state '{state}'. Use: {', '.join(sorted(STATES))}")
    print(f"\nMoving {side} to {state_key} ({STATES[state_key]:.0f} deg logical)")
    move_servo(pwms, current, side, STATES[state_key])


def manual_adjust(pwms, current, side, delta):
    target = clamp_angle(current[side] + delta)
    print(f"\nManual {side} adjustment: {current[side]:.0f} deg {delta:+.0f} deg -> {target:.0f} deg")
    move_servo(pwms, current, side, target)


def wait_for_enter(label):
    input(f"\nPress Enter: {label}...")


def run_default_sequence(pwms, current):
    print("\nDefault sequence starts from assumed neutral/open (90 deg logical).")
    print("Right servo direction is inverted automatically.")

    sequence = [
        ("left", "neutral"),
        ("left", "closed"),
        ("left", "neutral"),
        ("left", "open"),
        ("right", "neutral"),
        ("right", "closed"),
        ("right", "neutral"),
        ("right", "open"),
    ]

    for side, state in sequence:
        wait_for_enter(f"{side} -> {state}")
        move_to_state(pwms, current, side, state)


def park_neutral(pwms, current):
    print("\nParking both paddles at neutral/open.")
    move_servo(pwms, current, "left", NEUTRAL_ANGLE)
    move_servo(pwms, current, "right", NEUTRAL_ANGLE)


def cleanup(pwms):
    if not HARDWARE:
        return
    for pwm in pwms.values():
        pwm.stop()
    GPIO.cleanup()
    print("GPIO cleaned up.")


def build_parser():
    parser = argparse.ArgumentParser(
        description="Test left/right paddle servo states and small manual movements."
    )
    parser.add_argument("-l", "--left-delta", type=float, help="Move left servo by this many logical degrees.")
    parser.add_argument("-r", "--right-delta", type=float, help="Move right servo by this many logical degrees.")
    parser.add_argument("--left", choices=sorted(STATES), help="Move left servo to a named state.")
    parser.add_argument("--right", choices=sorted(STATES), help="Move right servo to a named state.")
    parser.add_argument("--both", choices=sorted(STATES), help="Move both servos to a named state.")
    parser.add_argument("--no-park", action="store_true", help="Do not park at neutral before cleanup.")
    return parser


def main():
    args = build_parser().parse_args()
    current = {
        "left": NEUTRAL_ANGLE,
        "right": NEUTRAL_ANGLE,
    }

    print("\nSECon26 Paddle Servo Test 3")
    print("===========================")
    print("States: neutral/open=90 deg, predeploy=135 deg, closed=0 deg")
    if HARDWARE:
        print("HARDWARE mode - paddles will move.")
    else:
        print("SIMULATION mode - no GPIO output.")

    pwms = setup()
    try:
        apply_angle(pwms, "left", current["left"])
        apply_angle(pwms, "right", current["right"])
        time.sleep(SETTLE_DELAY)

        any_command = any([
            args.left_delta is not None,
            args.right_delta is not None,
            args.left,
            args.right,
            args.both,
        ])

        if args.both:
            move_to_state(pwms, current, "left", args.both)
            move_to_state(pwms, current, "right", args.both)
        if args.left:
            move_to_state(pwms, current, "left", args.left)
        if args.right:
            move_to_state(pwms, current, "right", args.right)
        if args.left_delta is not None:
            manual_adjust(pwms, current, "left", args.left_delta)
        if args.right_delta is not None:
            manual_adjust(pwms, current, "right", args.right_delta)
        if not any_command:
            run_default_sequence(pwms, current)
    except KeyboardInterrupt:
        print("\nAborted by user.")
    finally:
        if not args.no_park:
            park_neutral(pwms, current)
        cleanup(pwms)


if __name__ == "__main__":
    main()

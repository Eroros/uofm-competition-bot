#!/usr/bin/env python3
"""
servo_motor_test.py
Hardware test script for all motors and servos.
Servos move in small steps to avoid mechanical stress.

Run directly on the Pi (no ROS needed):
  python3 servo_motor_test.py
"""

import time
import sys

try:
    import RPi.GPIO as GPIO
    HARDWARE = True
except ImportError:
    HARDWARE = False
    print('[WARNING] RPi.GPIO not available — running in simulation mode')

# ── Motor GPIO (BCM) ───────────────────────────────────────────────────────────
FL_PWM, FL_IN1, FL_IN2 = 12, 5,  6
FR_PWM, FR_IN1, FR_IN2 = 13, 19, 26
RL_PWM, RL_IN1, RL_IN2 = 18, 17, 27
RR_PWM, RR_IN1, RR_IN2 = 25, 22, 24
DRV1_STBY = 21
DRV2_STBY = 20

# ── Servo GPIO (BCM) ───────────────────────────────────────────────────────────
PADDLE_LEFT  = 23
PADDLE_RIGHT = 16
CRANK        = 7

# ── PWM settings ───────────────────────────────────────────────────────────────
MOTOR_PWM_FREQ = 1000
SERVO_PWM_FREQ = 50
MOTOR_SPEED    = 50    # % duty cycle (0-100)

# ── Servo angles ───────────────────────────────────────────────────────────────
PADDLE_OPEN    = 90.0
PADDLE_CLOSED  = 30.0
PADDLE_RELEASE = 150.0
CRANK_DOWN     = 0.0
CRANK_UP       = 180.0

# ── Servo sweep settings ───────────────────────────────────────────────────────
STEP_SIZE      = 2.0    # degrees per step — smaller = smoother
STEP_DELAY     = 0.02   # seconds between steps — increase to slow down further


def angle_to_duty(angle):
    pulse_us = 500 + (angle / 180.0) * 2000
    return (pulse_us / 20000.0) * 100.0


def sweep_servo(pwm, from_angle, to_angle, step_size=STEP_SIZE, step_delay=STEP_DELAY):
    """Smoothly move a servo from one angle to another in small steps."""
    if not HARDWARE:
        print(f'    [SIM] Sweep {from_angle:.0f}° -> {to_angle:.0f}°')
        return
    step = step_size if to_angle > from_angle else -step_size
    current = from_angle
    while (step > 0 and current < to_angle) or (step < 0 and current > to_angle):
        current += step
        current = max(0.0, min(180.0, current))
        pwm.ChangeDutyCycle(angle_to_duty(current))
        time.sleep(step_delay)
    # Ensure we land exactly on target
    pwm.ChangeDutyCycle(angle_to_duty(to_angle))


def sweep_paddles(pwms, from_angle, to_angle):
    """Sweep both paddle servos together smoothly."""
    if not HARDWARE:
        print(f'    [SIM] Paddles sweep {from_angle:.0f}° -> {to_angle:.0f}°')
        return
    step = STEP_SIZE if to_angle > from_angle else -STEP_SIZE
    current = from_angle
    while (step > 0 and current < to_angle) or (step < 0 and current > to_angle):
        current += step
        current = max(0.0, min(180.0, current))
        dc = angle_to_duty(current)
        pwms['pl'].ChangeDutyCycle(dc)
        pwms['pr'].ChangeDutyCycle(dc)
        time.sleep(STEP_DELAY)
    dc = angle_to_duty(to_angle)
    pwms['pl'].ChangeDutyCycle(dc)
    pwms['pr'].ChangeDutyCycle(dc)


def setup():
    if not HARDWARE:
        return None
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    pins = [FL_IN1, FL_IN2, FR_IN1, FR_IN2,
            RL_IN1, RL_IN2, RR_IN1, RR_IN2,
            FL_PWM, FR_PWM, RL_PWM, RR_PWM,
            DRV1_STBY, DRV2_STBY,
            PADDLE_LEFT, PADDLE_RIGHT, CRANK]
    for p in pins:
        GPIO.setup(p, GPIO.OUT)
        GPIO.output(p, GPIO.LOW)

    GPIO.output(DRV1_STBY, GPIO.HIGH)
    GPIO.output(DRV2_STBY, GPIO.HIGH)

    pwms = {
        'fl': GPIO.PWM(FL_PWM, MOTOR_PWM_FREQ),
        'fr': GPIO.PWM(FR_PWM, MOTOR_PWM_FREQ),
        'rl': GPIO.PWM(RL_PWM, MOTOR_PWM_FREQ),
        'rr': GPIO.PWM(RR_PWM, MOTOR_PWM_FREQ),
        'pl': GPIO.PWM(PADDLE_LEFT,  SERVO_PWM_FREQ),
        'pr': GPIO.PWM(PADDLE_RIGHT, SERVO_PWM_FREQ),
        'cr': GPIO.PWM(CRANK,        SERVO_PWM_FREQ),
    }
    for pwm in pwms.values():
        pwm.start(0)

    # Gently park servos at neutral on startup
    print('  Parking servos at neutral positions...')
    sweep_paddles(pwms, 0.0, PADDLE_OPEN)
    sweep_servo(pwms['cr'], 0.0, CRANK_DOWN)
    time.sleep(0.5)

    return pwms


def set_motor(pwms, name_pwm, in1, in2, duty):
    if not HARDWARE:
        return
    dc = abs(duty)
    if duty > 0:
        GPIO.output(in1, GPIO.HIGH)
        GPIO.output(in2, GPIO.LOW)
    elif duty < 0:
        GPIO.output(in1, GPIO.LOW)
        GPIO.output(in2, GPIO.HIGH)
    else:
        GPIO.output(in1, GPIO.LOW)
        GPIO.output(in2, GPIO.LOW)
        dc = 0
    pwms[name_pwm].ChangeDutyCycle(dc)


def stop_all_motors(pwms):
    if not HARDWARE:
        return
    for name in ['fl', 'fr', 'rl', 'rr']:
        pwms[name].ChangeDutyCycle(0)
    for in_pin in [FL_IN1, FL_IN2, FR_IN1, FR_IN2,
                   RL_IN1, RL_IN2, RR_IN1, RR_IN2]:
        GPIO.output(in_pin, GPIO.LOW)


def cleanup(pwms):
    if not HARDWARE:
        return
    stop_all_motors(pwms)
    print('\n  Gently parking servos before shutdown...')
    sweep_paddles(pwms, PADDLE_OPEN, PADDLE_OPEN)
    sweep_servo(pwms['cr'], CRANK_UP, CRANK_DOWN)
    time.sleep(0.5)
    for pwm in pwms.values():
        pwm.stop()
    GPIO.output(DRV1_STBY, GPIO.LOW)
    GPIO.output(DRV2_STBY, GPIO.LOW)
    GPIO.cleanup()
    print('  GPIO cleaned up.')


def section(title):
    print(f'\n{"="*50}')
    print(f'  {title}')
    print(f'{"="*50}')


def run_tests(pwms):

    # ── TEST 1: Drive motors ───────────────────────────────────────────────────
    section('TEST 1: Drive Motors')

    print('  Forward...')
    set_motor(pwms, 'fl', FL_IN1, FL_IN2,  MOTOR_SPEED)
    set_motor(pwms, 'rl', RL_IN1, RL_IN2,  MOTOR_SPEED)
    set_motor(pwms, 'fr', FR_IN1, FR_IN2, -MOTOR_SPEED)
    set_motor(pwms, 'rr', RR_IN1, RR_IN2, -MOTOR_SPEED)
    time.sleep(1.5)
    stop_all_motors(pwms)
    time.sleep(0.5)

    print('  Backward...')
    set_motor(pwms, 'fl', FL_IN1, FL_IN2, -MOTOR_SPEED)
    set_motor(pwms, 'rl', RL_IN1, RL_IN2, -MOTOR_SPEED)
    set_motor(pwms, 'fr', FR_IN1, FR_IN2,  MOTOR_SPEED)
    set_motor(pwms, 'rr', RR_IN1, RR_IN2,  MOTOR_SPEED)
    time.sleep(1.5)
    stop_all_motors(pwms)
    time.sleep(0.5)

    print('  Turn left...')
    set_motor(pwms, 'fl', FL_IN1, FL_IN2, -MOTOR_SPEED)
    set_motor(pwms, 'rl', RL_IN1, RL_IN2, -MOTOR_SPEED)
    set_motor(pwms, 'fr', FR_IN1, FR_IN2, -MOTOR_SPEED)
    set_motor(pwms, 'rr', RR_IN1, RR_IN2, -MOTOR_SPEED)
    time.sleep(1.5)
    stop_all_motors(pwms)
    time.sleep(0.5)

    print('  Turn right...')
    set_motor(pwms, 'fl', FL_IN1, FL_IN2,  MOTOR_SPEED)
    set_motor(pwms, 'rl', RL_IN1, RL_IN2,  MOTOR_SPEED)
    set_motor(pwms, 'fr', FR_IN1, FR_IN2,  MOTOR_SPEED)
    set_motor(pwms, 'rr', RR_IN1, RR_IN2,  MOTOR_SPEED)
    time.sleep(1.5)
    stop_all_motors(pwms)
    print('  Motors OK')

    # ── TEST 2: Paddle servos ─────────────────────────────────────────────────
    section('TEST 2: Paddle Servos — Duck Capture & Release')

    print('  Opening paddles to neutral (90°)...')
    sweep_paddles(pwms, PADDLE_OPEN, PADDLE_OPEN)
    time.sleep(0.5)

    print('  Closing paddles — simulating duck capture (90° -> 30°)...')
    sweep_paddles(pwms, PADDLE_OPEN, PADDLE_CLOSED)
    time.sleep(1.0)

    print('  Opening paddles back to neutral (30° -> 90°)...')
    sweep_paddles(pwms, PADDLE_CLOSED, PADDLE_OPEN)
    time.sleep(0.5)

    print('  Releasing paddles — simulating duck release (90° -> 150°)...')
    sweep_paddles(pwms, PADDLE_OPEN, PADDLE_RELEASE)
    time.sleep(1.0)

    print('  Returning paddles to neutral (150° -> 90°)...')
    sweep_paddles(pwms, PADDLE_RELEASE, PADDLE_OPEN)
    time.sleep(0.5)

    print('  Paddle servos OK')

    # ── TEST 3: Crank servo ───────────────────────────────────────────────────
    section('TEST 3: Crank Servo — Up/Down')

    print('  Crank at down position (0°)...')
    sweep_servo(pwms['cr'], CRANK_DOWN, CRANK_DOWN)
    time.sleep(0.5)

    print('  Crank sweeping up (0° -> 180°)...')
    sweep_servo(pwms['cr'], CRANK_DOWN, CRANK_UP)
    time.sleep(1.0)

    print('  Crank sweeping back down (180° -> 0°)...')
    sweep_servo(pwms['cr'], CRANK_UP, CRANK_DOWN)
    time.sleep(0.5)

    print('  Crank servo OK')

    # ── TEST 4: Full duck capture sequence ────────────────────────────────────
    section('TEST 4: Full Duck Capture Sequence')

    print('  Driving toward duck...')
    set_motor(pwms, 'fl', FL_IN1, FL_IN2,  MOTOR_SPEED)
    set_motor(pwms, 'rl', RL_IN1, RL_IN2,  MOTOR_SPEED)
    set_motor(pwms, 'fr', FR_IN1, FR_IN2, -MOTOR_SPEED)
    set_motor(pwms, 'rr', RR_IN1, RR_IN2, -MOTOR_SPEED)
    time.sleep(1.0)
    stop_all_motors(pwms)
    time.sleep(0.3)

    print('  Gently capturing duck...')
    sweep_paddles(pwms, PADDLE_OPEN, PADDLE_CLOSED)
    time.sleep(0.8)

    print('  Transporting duck to landing zone...')
    set_motor(pwms, 'fl', FL_IN1, FL_IN2,  MOTOR_SPEED)
    set_motor(pwms, 'rl', RL_IN1, RL_IN2,  MOTOR_SPEED)
    set_motor(pwms, 'fr', FR_IN1, FR_IN2, -MOTOR_SPEED)
    set_motor(pwms, 'rr', RR_IN1, RR_IN2, -MOTOR_SPEED)
    time.sleep(1.0)
    stop_all_motors(pwms)
    time.sleep(0.3)

    print('  Gently releasing duck...')
    sweep_paddles(pwms, PADDLE_CLOSED, PADDLE_RELEASE)
    time.sleep(0.8)

    print('  Returning paddles to neutral...')
    sweep_paddles(pwms, PADDLE_RELEASE, PADDLE_OPEN)

    print('  Full sequence OK')

    section('ALL TESTS PASSED')


def main():
    print('\nSECon26 Motor & Servo Test Script')
    print('==================================')
    if not HARDWARE:
        print('Running in SIMULATION mode — no GPIO output')
    else:
        print('Running in HARDWARE mode — motors and servos will move!')
        print('Elevate robot off ground before starting.')
        print(f'Servo step size: {STEP_SIZE}° per step, {STEP_DELAY*1000:.0f}ms delay')

    input('\nPress Enter to start tests (Ctrl+C to abort)...')

    pwms = setup()
    try:
        run_tests(pwms)
    except KeyboardInterrupt:
        print('\nTest aborted by user')
    finally:
        if pwms:
            cleanup(pwms)


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
paddle_test.py
Paddle servo test with mirrored right servo.

Left paddle:  90° = neutral, 65° = closed, 130° = predeploy
Right paddle: 90° = neutral, 115° = closed, 50° = predeploy

Sequence:
  1. Both to neutral (90°)
  2. Both close (left 65°, right 115°)
  3. Both back to neutral (90°)
  4. Both to predeploy (left 130°, right 50°)
  5. Both back to neutral (90°)

Run on Pi:
  python3 paddle_test.py
"""

import time

try:
    import RPi.GPIO as GPIO
    HARDWARE = True
except ImportError:
    HARDWARE = False
    print('[WARNING] Simulation mode — no GPIO')

# ── Servo GPIO (BCM) ───────────────────────────────────────────────────────────
PADDLE_LEFT_PIN  = 23
PADDLE_RIGHT_PIN = 16

SERVO_PWM_FREQ = 50

# ── Paddle angles ──────────────────────────────────────────────────────────────
# Left paddle
LEFT_NEUTRAL   = 90.0
LEFT_CLOSED    = 65.0    # 25° inward from neutral
LEFT_PREDEPLOY = 130.0   # spread outward

# Right paddle (mirrored — opposite direction)
RIGHT_NEUTRAL   = 90.0
RIGHT_CLOSED    = 115.0  # 25° inward from neutral (mirrored)
RIGHT_PREDEPLOY = 50.0   # spread outward (mirrored)

# ── Speed ──────────────────────────────────────────────────────────────────────
STEP_DEG   = 2.0
STEP_PAUSE = 0.08   # seconds between pulses — increase to slow down further


def angle_to_duty(angle):
    pulse_us = 500 + (angle / 180.0) * 2000
    return (pulse_us / 20000.0) * 100.0


def sweep(pwm, label, from_angle, to_angle):
    """Sweep one servo smoothly from from_angle to to_angle."""
    print(f'    {label}: {from_angle:.0f}° → {to_angle:.0f}° ', end='', flush=True)
    if not HARDWARE:
        print('[SIM]')
        return
    step = STEP_DEG if to_angle >= from_angle else -STEP_DEG
    current = from_angle
    while True:
        current += step
        if (step > 0 and current >= to_angle) or (step < 0 and current <= to_angle):
            current = to_angle
        pwm.ChangeDutyCycle(angle_to_duty(current))
        print('.', end='', flush=True)
        time.sleep(STEP_PAUSE)
        if current == to_angle:
            break
    print(' done')


def setup():
    if not HARDWARE:
        return None, None
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(PADDLE_LEFT_PIN,  GPIO.OUT)
    GPIO.setup(PADDLE_RIGHT_PIN, GPIO.OUT)
    pwm_l = GPIO.PWM(PADDLE_LEFT_PIN,  SERVO_PWM_FREQ)
    pwm_r = GPIO.PWM(PADDLE_RIGHT_PIN, SERVO_PWM_FREQ)
    pwm_l.start(0)
    pwm_r.start(0)
    return pwm_l, pwm_r


def cleanup(pwm_l, pwm_r):
    if not HARDWARE:
        return
    print('\n  Returning to neutral before shutdown...')
    sweep(pwm_l, 'Left ', LEFT_NEUTRAL,  LEFT_NEUTRAL)
    sweep(pwm_r, 'Right', RIGHT_NEUTRAL, RIGHT_NEUTRAL)
    pwm_l.stop()
    pwm_r.stop()
    GPIO.cleanup()
    print('  Done.')


def wait(msg):
    input(f'\n  >> {msg}\n     Press Enter to continue...')


def run_tests(pwm_l, pwm_r):

    print(f'\n  Angle reference:')
    print(f'    Left  — Neutral: {LEFT_NEUTRAL}°  Close: {LEFT_CLOSED}°  Predeploy: {LEFT_PREDEPLOY}°')
    print(f'    Right — Neutral: {RIGHT_NEUTRAL}°  Close: {RIGHT_CLOSED}°  Predeploy: {RIGHT_PREDEPLOY}°')
    print(f'  Speed: {STEP_DEG}° per pulse, {STEP_PAUSE*1000:.0f}ms delay')

    # ── Step 1: Both to neutral ────────────────────────────────────────────────
    wait('Step 1: Move both paddles to NEUTRAL (90°)')
    sweep(pwm_l, 'Left ', 0.0, LEFT_NEUTRAL)
    sweep(pwm_r, 'Right', 0.0, RIGHT_NEUTRAL)
    time.sleep(1.0)
    print('  >> Paddles should be straight forward at 90°')
    input('     Press Enter to continue...')

    # ── Step 2: Both close ─────────────────────────────────────────────────────
    wait(f'Step 2: CLOSE both paddles (Left → {LEFT_CLOSED}°, Right → {RIGHT_CLOSED}°)')
    sweep(pwm_l, 'Left ', LEFT_NEUTRAL, LEFT_CLOSED)
    sweep(pwm_r, 'Right', RIGHT_NEUTRAL, RIGHT_CLOSED)
    time.sleep(1.0)
    print('  >> Paddles should be 25° inward — check they are not touching')
    input('     Press Enter to continue...')

    # ── Step 3: Back to neutral ────────────────────────────────────────────────
    wait('Step 3: Return both paddles to NEUTRAL (90°)')
    sweep(pwm_l, 'Left ', LEFT_CLOSED, LEFT_NEUTRAL)
    sweep(pwm_r, 'Right', RIGHT_CLOSED, RIGHT_NEUTRAL)
    time.sleep(1.0)
    print('  >> Paddles should be back to straight forward')
    input('     Press Enter to continue...')

    # ── Step 4: Both to predeploy ──────────────────────────────────────────────
    wait(f'Step 4: PREDEPLOY both paddles (Left → {LEFT_PREDEPLOY}°, Right → {RIGHT_PREDEPLOY}°)')
    sweep(pwm_l, 'Left ', LEFT_NEUTRAL, LEFT_PREDEPLOY)
    sweep(pwm_r, 'Right', RIGHT_NEUTRAL, RIGHT_PREDEPLOY)
    time.sleep(1.0)
    print('  >> Paddles should be spread outward — check clearance from frame')
    input('     Press Enter to continue...')

    # ── Step 5: Back to neutral ────────────────────────────────────────────────
    wait('Step 5: Return both paddles to NEUTRAL (90°)')
    sweep(pwm_l, 'Left ', LEFT_PREDEPLOY, LEFT_NEUTRAL)
    sweep(pwm_r, 'Right', RIGHT_PREDEPLOY, RIGHT_NEUTRAL)
    time.sleep(1.0)

    print('\n  Paddle test complete!')
    print(f'\n  Once happy with these angles, update dsservo_driver.py:')
    print(f'    PADDLE_OPEN      = {LEFT_NEUTRAL}   (both)')
    print(f'    PADDLE_CLOSED_L  = {LEFT_CLOSED}    (left)')
    print(f'    PADDLE_CLOSED_R  = {RIGHT_CLOSED}   (right)')
    print(f'    PADDLE_DEPLOY_L  = {LEFT_PREDEPLOY} (left)')
    print(f'    PADDLE_DEPLOY_R  = {RIGHT_PREDEPLOY} (right)')


def main():
    print('\nPaddle Servo Test — Mirrored Configuration')
    print('============================================')
    if not HARDWARE:
        print('SIMULATION mode')
    else:
        print('HARDWARE mode — robot should be elevated!')

    input('\nPress Enter to begin (Ctrl+C to abort)...')

    pwm_l, pwm_r = setup()
    try:
        run_tests(pwm_l, pwm_r)
    except KeyboardInterrupt:
        print('\nAborted')
    finally:
        if pwm_l:
            cleanup(pwm_l, pwm_r)


if __name__ == '__main__':
    main()

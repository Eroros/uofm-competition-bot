#!/usr/bin/env python3
"""
paddle_test.py
Safe paddle servo test with configurable boundaries.
Paddles will NOT exceed the set min/max angles.

Tune PADDLE_MIN and PADDLE_MAX to your physical limits
before running the full mission script.

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
PADDLE_LEFT  = 23
PADDLE_RIGHT = 16

SERVO_PWM_FREQ = 50

# ── SAFE BOUNDARIES — tune these first ────────────────────────────────────────
# Start conservative and widen gradually until paddles are where you want them
# PADDLE_MIN = fully closed (capturing duck) — increase if paddles hit each other
# PADDLE_MAX = fully open/release — decrease if paddles hit the frame
PADDLE_MIN    = -65.0   # degrees — closed/capture position (safe start)
PADDLE_NEUTRAL = 65.0  # degrees — resting neutral
PADDLE_MAX    = 65.0  # degrees — open/release position (safe start)

# ── Speed ──────────────────────────────────────────────────────────────────────
STEP_DEG   = 2.0    # degrees per pulse
STEP_PAUSE = 0.08   # seconds between pulses — increase to slow down


def angle_to_duty(angle):
    # Clamp to safe boundaries
    angle = max(PADDLE_MIN, min(PADDLE_MAX, angle))
    pulse_us = 500 + (angle / 180.0) * 2000
    return (pulse_us / 20000.0) * 100.0


def sweep_one(pwm, label, from_angle, to_angle):
    """Sweep one paddle servo with boundary enforcement."""
    from_angle = max(PADDLE_MIN, min(PADDLE_MAX, from_angle))
    to_angle   = max(PADDLE_MIN, min(PADDLE_MAX, to_angle))
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
    GPIO.setup(PADDLE_LEFT,  GPIO.OUT)
    GPIO.setup(PADDLE_RIGHT, GPIO.OUT)
    pwm_l = GPIO.PWM(PADDLE_LEFT,  SERVO_PWM_FREQ)
    pwm_r = GPIO.PWM(PADDLE_RIGHT, SERVO_PWM_FREQ)
    pwm_l.start(0)
    pwm_r.start(0)
    return pwm_l, pwm_r


def cleanup(pwm_l, pwm_r):
    if not HARDWARE:
        return
    print('\n  Parking paddles at neutral...')
    sweep_one(pwm_l, 'Left ', PADDLE_NEUTRAL, PADDLE_NEUTRAL)
    sweep_one(pwm_r, 'Right', PADDLE_NEUTRAL, PADDLE_NEUTRAL)
    pwm_l.stop()
    pwm_r.stop()
    GPIO.cleanup()
    print('  Done.')


def wait(msg):
    input(f'\n  >> {msg}\n     Press Enter to continue...')


def run_tests(pwm_l, pwm_r):

    print(f'\n  Safe boundaries:')
    print(f'    PADDLE_MIN (closed) = {PADDLE_MIN}°')
    print(f'    PADDLE_NEUTRAL      = {PADDLE_NEUTRAL}°')
    print(f'    PADDLE_MAX (open)   = {PADDLE_MAX}°')
    print(f'  Step: {STEP_DEG}° per pulse, {STEP_PAUSE*1000:.0f}ms delay')

    # ── Step 1: Move to neutral ────────────────────────────────────────────────
    wait('Step 1: Move LEFT paddle to neutral (90°)')
    sweep_one(pwm_l, 'Left ', 90.0, PADDLE_NEUTRAL)

    wait('Step 2: Move RIGHT paddle to neutral (90°)')
    sweep_one(pwm_r, 'Right', -90.0, PADDLE_NEUTRAL)
    time.sleep(0.5)

    # ── Step 2: Close paddles (capture) ───────────────────────────────────────
    wait(f'Step 3: Close LEFT paddle to {PADDLE_MIN}° (capture position)')
    sweep_one(pwm_l, 'Left ', PADDLE_NEUTRAL, PADDLE_MIN)
    time.sleep(0.5)

    wait(f'Step 4: Close RIGHT paddle to {PADDLE_MIN}° (capture position)')
    sweep_one(pwm_r, 'Right', PADDLE_NEUTRAL, PADDLE_MIN)
    time.sleep(1.0)
    print('  >> Check: are paddles touching each other or the frame?')
    print('     If yes — increase PADDLE_MIN at the top of this file')
    input('     Press Enter to continue...')

    # ── Step 3: Back to neutral ────────────────────────────────────────────────
    wait('Step 5: Return LEFT paddle to neutral')
    sweep_one(pwm_l, 'Left ', PADDLE_MIN, PADDLE_NEUTRAL)

    wait('Step 6: Return RIGHT paddle to neutral')
    sweep_one(pwm_r, 'Right', PADDLE_MIN, PADDLE_NEUTRAL)
    time.sleep(0.5)

    # ── Step 4: Open paddles (release) ────────────────────────────────────────
    wait(f'Step 7: Open LEFT paddle to {PADDLE_MAX}° (release position)')
    sweep_one(pwm_l, 'Left ', PADDLE_NEUTRAL, PADDLE_MAX)
    time.sleep(0.5)

    wait(f'Step 8: Open RIGHT paddle to {PADDLE_MAX}° (release position)')
    sweep_one(pwm_r, 'Right', PADDLE_NEUTRAL, PADDLE_MAX)
    time.sleep(1.0)
    print('  >> Check: are paddles hitting the frame or robot body?')
    print('     If yes — decrease PADDLE_MAX at the top of this file')
    input('     Press Enter to continue...')

    # ── Step 5: Return to neutral ──────────────────────────────────────────────
    wait('Step 9: Return both paddles to neutral')
    sweep_one(pwm_l, 'Left ', PADDLE_MAX, PADDLE_NEUTRAL)
    sweep_one(pwm_r, 'Right', PADDLE_MAX, PADDLE_NEUTRAL)

    print('\n  ✓ Paddle test complete!')
    print(f'  If everything looked good, update dsservo_driver.py:')
    print(f'    PADDLE_OPEN    = {PADDLE_NEUTRAL}')
    print(f'    PADDLE_CLOSED  = {PADDLE_MIN}')
    print(f'    PADDLE_EXTEND  = {PADDLE_MAX}')


def main():
    print('\nPaddle Servo Boundary Test')
    print('===========================')
    print('Tests one paddle at a time with safe angle limits.')
    print('Ctrl+C at any time to abort safely.')
    if not HARDWARE:
        print('SIMULATION mode')

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

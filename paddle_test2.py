#!/usr/bin/env python3
"""
paddle_test2.py
Paddle servo test — corrected closing direction.

Left paddle:  90° = neutral, 115° = closed (forward), 65° = predeploy
Right paddle: 90° = neutral, 65° = closed (forward), 115° = predeploy

Run on Pi:
  python3 paddle_test2.py
"""

import time

try:
    import RPi.GPIO as GPIO
    HARDWARE = True
except ImportError:
    HARDWARE = False
    print('[WARNING] Simulation mode — no GPIO')

PADDLE_LEFT_PIN  = 23
PADDLE_RIGHT_PIN = 16
SERVO_PWM_FREQ   = 50

# ── Paddle angles ──────────────────────────────────────────────────────────────
LEFT_NEUTRAL   = 90.0
LEFT_CLOSED    = 180.0   # closes forward
LEFT_PREDEPLOY = 30.0    # spreads outward

RIGHT_NEUTRAL   = 90.0
RIGHT_CLOSED    = 0.0   # closes forward (mirrored)
RIGHT_PREDEPLOY = 145.0  # spreads outward (mirrored)

STEP_DEG   = 2.0
STEP_PAUSE = 0.05


def angle_to_duty(angle):
    pulse_us = 500 + (angle / 180.0) * 2000
    return (pulse_us / 20000.0) * 100.0


def sweep(pwm, label, from_angle, to_angle):
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
    pwm_l.start(angle_to_duty(LEFT_NEUTRAL))
    pwm_r.start(angle_to_duty(RIGHT_NEUTRAL))
    return pwm_l, pwm_r


def cleanup(pwm_l, pwm_r):
    if not HARDWARE:
        return
    print('\n  Returning to neutral...')
    sweep(pwm_l, 'Left ', LEFT_NEUTRAL, LEFT_NEUTRAL)
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
    print('\n  Paddles physically at neutral — no movement until Enter.')

    # ── Step 1: Neutral → Close ────────────────────────────────────────────────
    wait(f'Step 1: CLOSE paddles forward (Left→{LEFT_CLOSED}°, Right→{RIGHT_CLOSED}°)')
    sweep(pwm_l, 'Left ', LEFT_NEUTRAL, LEFT_CLOSED)
    sweep(pwm_r, 'Right', RIGHT_NEUTRAL, RIGHT_CLOSED)
    time.sleep(1.0)
    print('  >> Paddles should close forward — check they are not touching')
    input('     Press Enter to continue...')

    # ── Step 2: Close → Neutral ────────────────────────────────────────────────
    wait(f'Step 2: Return to NEUTRAL (Left→{LEFT_NEUTRAL}°, Right→{RIGHT_NEUTRAL}°)')
    sweep(pwm_l, 'Left ', LEFT_CLOSED, LEFT_NEUTRAL)
    sweep(pwm_r, 'Right', RIGHT_CLOSED, RIGHT_NEUTRAL)
    time.sleep(1.0)
    print('  >> Paddles should be back to straight forward')
    input('     Press Enter to continue...')

    # ── Step 3: Neutral → Predeploy ───────────────────────────────────────────
    wait(f'Step 3: PREDEPLOY (Left→{LEFT_PREDEPLOY}°, Right→{RIGHT_PREDEPLOY}°)')
    sweep(pwm_l, 'Left ', LEFT_NEUTRAL, LEFT_PREDEPLOY)
    sweep(pwm_r, 'Right', RIGHT_NEUTRAL, RIGHT_PREDEPLOY)
    time.sleep(1.0)
    print('  >> Paddles should be spread outward — check clearance from frame')
    input('     Press Enter to continue...')

    # ── Step 4: Predeploy → Neutral ───────────────────────────────────────────
    wait(f'Step 4: Return to NEUTRAL (Left→{LEFT_NEUTRAL}°, Right→{RIGHT_NEUTRAL}°)')
    sweep(pwm_l, 'Left ', LEFT_PREDEPLOY, LEFT_NEUTRAL)
    sweep(pwm_r, 'Right', RIGHT_PREDEPLOY, RIGHT_NEUTRAL)
    time.sleep(1.0)

    print('\n  Paddle test 2 complete!')
    print(f'\n  Copy these into dsservo_driver.py when satisfied:')
    print(f'    LEFT_NEUTRAL    = {LEFT_NEUTRAL}')
    print(f'    LEFT_CLOSED     = {LEFT_CLOSED}')
    print(f'    LEFT_PREDEPLOY  = {LEFT_PREDEPLOY}')
    print(f'    RIGHT_NEUTRAL   = {RIGHT_NEUTRAL}')
    print(f'    RIGHT_CLOSED    = {RIGHT_CLOSED}')
    print(f'    RIGHT_PREDEPLOY = {RIGHT_PREDEPLOY}')


def main():
    print('\nPaddle Test 2 — Corrected Closing Direction')
    print('=============================================')
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

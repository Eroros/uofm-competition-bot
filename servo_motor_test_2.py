#!/usr/bin/env python3
"""
servo_motor_test.py
Hardware test — one servo at a time, 2 degree pulses, slow and controlled.

Run on Pi:
  python3 servo_motor_test.py
"""

import time

try:
    import RPi.GPIO as GPIO
    HARDWARE = True
except ImportError:
    HARDWARE = False
    print('[WARNING] RPi.GPIO not available — simulation mode')

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

MOTOR_PWM_FREQ = 1000
SERVO_PWM_FREQ = 50
MOTOR_SPEED    = 20

# ── Servo angles ───────────────────────────────────────────────────────────────
PADDLE_OPEN    = 90.0
PADDLE_CLOSED  = 30.0
PADDLE_RELEASE = 150.0
CRANK_DOWN     = 0.0
CRANK_UP       = 180.0

# ── Sweep speed ────────────────────────────────────────────────────────────────
STEP_DEG   = 2.0    # degrees per pulse
STEP_PAUSE = 0.15   # seconds between each pulse — increase to go slower


def angle_to_duty(angle):
    pulse_us = 500 + (angle / 180.0) * 2000
    return (pulse_us / 20000.0) * 100.0


def sweep(pwm, from_angle, to_angle, label='servo'):
    """Move one servo from_angle to to_angle one pulse at a time."""
    print(f'    {label}: {from_angle:.0f}° → {to_angle:.0f}° ', end='', flush=True)
    if not HARDWARE:
        print(f'[SIM]')
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
        return None
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    all_pins = [FL_IN1, FL_IN2, FR_IN1, FR_IN2,
                RL_IN1, RL_IN2, RR_IN1, RR_IN2,
                FL_PWM, FR_PWM, RL_PWM, RR_PWM,
                DRV1_STBY, DRV2_STBY,
                PADDLE_LEFT, PADDLE_RIGHT, CRANK]
    for p in all_pins:
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

    return pwms


def set_motor(pwms, name, in1, in2, duty):
    if not HARDWARE:
        return
    dc = abs(duty)
    GPIO.output(in1, GPIO.HIGH if duty > 0 else GPIO.LOW)
    GPIO.output(in2, GPIO.LOW  if duty > 0 else GPIO.HIGH)
    if duty == 0:
        GPIO.output(in1, GPIO.LOW)
        dc = 0
    pwms[name].ChangeDutyCycle(dc)


def stop_motors(pwms):
    if not HARDWARE:
        return
    for n in ['fl', 'fr', 'rl', 'rr']:
        pwms[n].ChangeDutyCycle(0)
    for p in [FL_IN1, FL_IN2, FR_IN1, FR_IN2, RL_IN1, RL_IN2, RR_IN1, RR_IN2]:
        GPIO.output(p, GPIO.LOW)


def cleanup(pwms):
    if not HARDWARE:
        return
    stop_motors(pwms)
    print('\n  Parking servos...')
    sweep(pwms['pl'], PADDLE_OPEN, PADDLE_OPEN, 'Paddle Left')
    sweep(pwms['pr'], PADDLE_OPEN, PADDLE_OPEN, 'Paddle Right')
    sweep(pwms['cr'], CRANK_UP,    CRANK_DOWN,  'Crank')
    time.sleep(0.3)
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


def wait(msg):
    input(f'\n  >> {msg} — press Enter to continue...')


def run_tests(pwms):

    # ── TEST 1: Paddle Left ───────────────────────────────────────────────────
    section('TEST 1: Paddle Left Servo')
    wait('Paddle Left will sweep open → closed → release → neutral')

    print('  Step 1: Open (neutral 90°)')
    sweep(pwms['pl'], 0.0, PADDLE_OPEN, 'Paddle Left')
    time.sleep(1.0)

    print('  Step 2: Close (capture duck 90° → 30°)')
    sweep(pwms['pl'], PADDLE_OPEN, PADDLE_CLOSED, 'Paddle Left')
    time.sleep(1.0)

    print('  Step 3: Back to neutral (30° → 90°)')
    sweep(pwms['pl'], PADDLE_CLOSED, PADDLE_OPEN, 'Paddle Left')
    time.sleep(1.0)

    print('  Step 4: Release (90° → 150°)')
    sweep(pwms['pl'], PADDLE_OPEN, PADDLE_RELEASE, 'Paddle Left')
    time.sleep(1.0)

    print('  Step 5: Return to neutral (150° → 90°)')
    sweep(pwms['pl'], PADDLE_RELEASE, PADDLE_OPEN, 'Paddle Left')
    print('  Paddle Left OK')

    # ── TEST 2: Paddle Right ──────────────────────────────────────────────────
    section('TEST 2: Paddle Right Servo')
    wait('Paddle Right will sweep open → closed → release → neutral')

    print('  Step 1: Open (neutral 90°)')
    sweep(pwms['pr'], 0.0, PADDLE_OPEN, 'Paddle Right')
    time.sleep(1.0)

    print('  Step 2: Close (capture duck 90° → 30°)')
    sweep(pwms['pr'], PADDLE_OPEN, PADDLE_CLOSED, 'Paddle Right')
    time.sleep(1.0)

    print('  Step 3: Back to neutral (30° → 90°)')
    sweep(pwms['pr'], PADDLE_CLOSED, PADDLE_OPEN, 'Paddle Right')
    time.sleep(1.0)

    print('  Step 4: Release (90° → 150°)')
    sweep(pwms['pr'], PADDLE_OPEN, PADDLE_RELEASE, 'Paddle Right')
    time.sleep(1.0)

    print('  Step 5: Return to neutral (150° → 90°)')
    sweep(pwms['pr'], PADDLE_RELEASE, PADDLE_OPEN, 'Paddle Right')
    print('  Paddle Right OK')

    # ── TEST 3: Crank servo ───────────────────────────────────────────────────
    section('TEST 3: Crank Servo — Up/Down')
    wait('Crank will sweep down → up → down')

    print('  Step 1: Down position (0°)')
    sweep(pwms['cr'], 0.0, CRANK_DOWN, 'Crank')
    time.sleep(1.0)

    print('  Step 2: Sweeping up (0° → 180°)')
    sweep(pwms['cr'], CRANK_DOWN, CRANK_UP, 'Crank')
    time.sleep(1.0)

    print('  Step 3: Sweeping back down (180° → 0°)')
    sweep(pwms['cr'], CRANK_UP, CRANK_DOWN, 'Crank')
    print('  Crank servo OK')

    # ── TEST 4: Both paddles together ─────────────────────────────────────────
    section('TEST 4: Both Paddles Together — Full Duck Capture')
    wait('Both paddles will open → close → release → neutral')

    print('  Step 1: Both open (90°)')
    sweep(pwms['pl'], PADDLE_OPEN, PADDLE_OPEN, 'Paddle Left')
    sweep(pwms['pr'], PADDLE_OPEN, PADDLE_OPEN, 'Paddle Right')
    time.sleep(1.0)

    print('  Step 2: Both close — capturing duck (90° → 30°)')
    sweep(pwms['pl'], PADDLE_OPEN, PADDLE_CLOSED, 'Paddle Left')
    sweep(pwms['pr'], PADDLE_OPEN, PADDLE_CLOSED, 'Paddle Right')
    time.sleep(1.0)

    print('  Step 3: Both release — dropping duck (30° → 150°)')
    sweep(pwms['pl'], PADDLE_CLOSED, PADDLE_RELEASE, 'Paddle Left')
    sweep(pwms['pr'], PADDLE_CLOSED, PADDLE_RELEASE, 'Paddle Right')
    time.sleep(1.0)

    print('  Step 4: Return to neutral (150° → 90°)')
    sweep(pwms['pl'], PADDLE_RELEASE, PADDLE_OPEN, 'Paddle Left')
    sweep(pwms['pr'], PADDLE_RELEASE, PADDLE_OPEN, 'Paddle Right')
    print('  Both paddles OK')

    # ── TEST 5: Drive motors ──────────────────────────────────────────────────
    section('TEST 5: Drive Motors')
    wait('Motors will run forward, backward, left, right (1.5s each)')

    print('  Forward...')
    set_motor(pwms, 'fl', FL_IN1, FL_IN2,  MOTOR_SPEED)
    set_motor(pwms, 'rl', RL_IN1, RL_IN2,  MOTOR_SPEED)
    set_motor(pwms, 'fr', FR_IN1, FR_IN2, -MOTOR_SPEED)
    set_motor(pwms, 'rr', RR_IN1, RR_IN2, -MOTOR_SPEED)
    time.sleep(1.5)
    stop_motors(pwms)
    time.sleep(0.5)

    print('  Backward...')
    set_motor(pwms, 'fl', FL_IN1, FL_IN2, -MOTOR_SPEED)
    set_motor(pwms, 'rl', RL_IN1, RL_IN2, -MOTOR_SPEED)
    set_motor(pwms, 'fr', FR_IN1, FR_IN2,  MOTOR_SPEED)
    set_motor(pwms, 'rr', RR_IN1, RR_IN2,  MOTOR_SPEED)
    time.sleep(1.5)
    stop_motors(pwms)
    time.sleep(0.5)

    print('  Turn left...')
    set_motor(pwms, 'fl', FL_IN1, FL_IN2, -MOTOR_SPEED)
    set_motor(pwms, 'rl', RL_IN1, RL_IN2, -MOTOR_SPEED)
    set_motor(pwms, 'fr', FR_IN1, FR_IN2, -MOTOR_SPEED)
    set_motor(pwms, 'rr', RR_IN1, RR_IN2, -MOTOR_SPEED)
    time.sleep(1.5)
    stop_motors(pwms)
    time.sleep(0.5)

    print('  Turn right...')
    set_motor(pwms, 'fl', FL_IN1, FL_IN2,  MOTOR_SPEED)
    set_motor(pwms, 'rl', RL_IN1, RL_IN2,  MOTOR_SPEED)
    set_motor(pwms, 'fr', FR_IN1, FR_IN2,  MOTOR_SPEED)
    set_motor(pwms, 'rr', RR_IN1, RR_IN2,  MOTOR_SPEED)
    time.sleep(1.5)
    stop_motors(pwms)
    print('  Motors OK')

    section('ALL TESTS COMPLETE')


def main():
    print('\nSECon26 Motor & Servo Test')
    print('===========================')
    print(f'Step size: {STEP_DEG}° per pulse, {STEP_PAUSE*1000:.0f}ms between pulses')
    if not HARDWARE:
        print('SIMULATION mode — no GPIO')
    else:
        print('HARDWARE mode — elevate robot before starting!')

    input('\nPress Enter to begin (Ctrl+C to abort at any time)...')

    pwms = setup()
    try:
        run_tests(pwms)
    except KeyboardInterrupt:
        print('\nAborted by user')
    finally:
        if pwms:
            cleanup(pwms)


if __name__ == '__main__':
    main()

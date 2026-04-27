#!/usr/bin/env python3
"""
duck_run_test.py
Hardcoded duck capture run test.

Sequence:
  1. Predeploy paddles (spread wide)
  2. Drive forward 4 seconds
  3. Close paddles (capture duck)
  4. Drive backward 4 seconds
  5. Release paddles (drop duck)
  6. Return paddles to neutral

Run on Pi:
  python3 duck_run_test.py
"""

import time

try:
    import RPi.GPIO as GPIO
    HARDWARE = True
except ImportError:
    HARDWARE = False
    print('[WARNING] Simulation mode — no GPIO')

# ── Motor GPIO (BCM) ───────────────────────────────────────────────────────────
FL_PWM, FL_IN1, FL_IN2 = 12, 5,  6
FR_PWM, FR_IN1, FR_IN2 = 13, 26, 19
RL_PWM, RL_IN1, RL_IN2 = 18, 17, 27
RR_PWM, RR_IN1, RR_IN2 = 25, 22, 24
DRV1_STBY = 21
DRV2_STBY = 20

# ── Servo GPIO (BCM) ───────────────────────────────────────────────────────────
PADDLE_LEFT_PIN  = 23
PADDLE_RIGHT_PIN = 16

MOTOR_PWM_FREQ = 1000
SERVO_PWM_FREQ = 50
MOTOR_SPEED    = 50

# ── Servo parameters ───────────────────────────────────────────────────────────
LEFT_NEUTRAL    = 90.0
LEFT_CLOSED     = 180.0
LEFT_PREDEPLOY  = 30.0
RIGHT_NEUTRAL   = 90.0
RIGHT_CLOSED    = 0.0
RIGHT_PREDEPLOY = 145.0

STEP_DEG   = 2.0
STEP_PAUSE = 0.05


def angle_to_duty(angle):
    pulse_us = 500 + (angle / 180.0) * 2000
    return (pulse_us / 20000.0) * 100.0


def sweep(pwm, label, from_angle, to_angle):
    print(f'  {label}: {from_angle:.0f}° → {to_angle:.0f}° ', end='', flush=True)
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
        return {}
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    all_pins = [FL_IN1, FL_IN2, FR_IN1, FR_IN2,
                RL_IN1, RL_IN2, RR_IN1, RR_IN2,
                FL_PWM, FR_PWM, RL_PWM, RR_PWM,
                DRV1_STBY, DRV2_STBY,
                PADDLE_LEFT_PIN, PADDLE_RIGHT_PIN]
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
        'pl': GPIO.PWM(PADDLE_LEFT_PIN,  SERVO_PWM_FREQ),
        'pr': GPIO.PWM(PADDLE_RIGHT_PIN, SERVO_PWM_FREQ),
    }
    for pwm in pwms.values():
        pwm.start(0)

    pwms['pl'].start(angle_to_duty(LEFT_NEUTRAL))
    pwms['pr'].start(angle_to_duty(RIGHT_NEUTRAL))

    return pwms


def drive_forward(pwms, duration):
    print(f'  Driving forward for {duration}s...')
    if not HARDWARE:
        time.sleep(duration)
        return
    pwms['fl'].ChangeDutyCycle(MOTOR_SPEED)
    pwms['rl'].ChangeDutyCycle(MOTOR_SPEED)
    pwms['fr'].ChangeDutyCycle(MOTOR_SPEED)
    pwms['rr'].ChangeDutyCycle(MOTOR_SPEED)
    GPIO.output(FL_IN1, GPIO.HIGH); GPIO.output(FL_IN2, GPIO.LOW)
    GPIO.output(RL_IN1, GPIO.HIGH); GPIO.output(RL_IN2, GPIO.LOW)
    GPIO.output(FR_IN1, GPIO.LOW);  GPIO.output(FR_IN2, GPIO.HIGH)
    GPIO.output(RR_IN1, GPIO.LOW);  GPIO.output(RR_IN2, GPIO.HIGH)
    time.sleep(duration)


def drive_backward(pwms, duration):
    print(f'  Driving backward for {duration}s...')
    if not HARDWARE:
        time.sleep(duration)
        return
    pwms['fl'].ChangeDutyCycle(MOTOR_SPEED)
    pwms['rl'].ChangeDutyCycle(MOTOR_SPEED)
    pwms['fr'].ChangeDutyCycle(MOTOR_SPEED)
    pwms['rr'].ChangeDutyCycle(MOTOR_SPEED)
    GPIO.output(FL_IN1, GPIO.LOW);  GPIO.output(FL_IN2, GPIO.HIGH)
    GPIO.output(RL_IN1, GPIO.LOW);  GPIO.output(RL_IN2, GPIO.HIGH)
    GPIO.output(FR_IN1, GPIO.HIGH); GPIO.output(FR_IN2, GPIO.LOW)
    GPIO.output(RR_IN1, GPIO.HIGH); GPIO.output(RR_IN2, GPIO.LOW)
    time.sleep(duration)


def stop(pwms):
    if not HARDWARE:
        return
    for n in ['fl', 'fr', 'rl', 'rr']:
        pwms[n].ChangeDutyCycle(0)
    for p in [FL_IN1, FL_IN2, FR_IN1, FR_IN2,
              RL_IN1, RL_IN2, RR_IN1, RR_IN2]:
        GPIO.output(p, GPIO.LOW)


def cleanup(pwms):
    if not HARDWARE:
        return
    stop(pwms)
    sweep(pwms['pl'], 'Left ', LEFT_NEUTRAL, LEFT_NEUTRAL)
    sweep(pwms['pr'], 'Right', RIGHT_NEUTRAL, RIGHT_NEUTRAL)
    for pwm in pwms.values():
        pwm.stop()
    GPIO.output(DRV1_STBY, GPIO.LOW)
    GPIO.output(DRV2_STBY, GPIO.LOW)
    GPIO.cleanup()
    print('  GPIO cleaned up.')


def main():
    print('\nDuck Run Test')
    print('==============')
    print('Sequence: predeploy → forward 4s → close → backward 4s → release → neutral')
    if not HARDWARE:
        print('SIMULATION mode')
    else:
        print('HARDWARE mode — place duck in front of robot before starting!')

    input('\nPress Enter to begin (Ctrl+C to abort)...')

    pwms = setup()

    try:
        # ── Step 1: Predeploy ──────────────────────────────────────────────────
        print('\n[1] Predeploying paddles...')
        sweep(pwms['pl'], 'Left ', LEFT_NEUTRAL,   LEFT_PREDEPLOY)
        sweep(pwms['pr'], 'Right', RIGHT_NEUTRAL,  RIGHT_PREDEPLOY)
        time.sleep(0.5)

        # ── Step 2: Drive forward ──────────────────────────────────────────────
        print('\n[2] Driving forward...')
        drive_forward(pwms, 0.5)
        stop(pwms)
        print('  Stopped.')
        time.sleep(0.5)

        # ── Step 3: Close paddles ──────────────────────────────────────────────
        print('\n[3] Closing paddles to capture duck...')
        sweep(pwms['pl'], 'Left ', LEFT_PREDEPLOY,  LEFT_CLOSED)
        sweep(pwms['pr'], 'Right', RIGHT_PREDEPLOY, RIGHT_CLOSED)
        time.sleep(0.5)
        print('  Duck captured!')

        # ── Step 4: Drive backward ─────────────────────────────────────────────
        print('\n[4] Driving backward...')
        drive_backward(pwms, 0.5)
        stop(pwms)
        print('  Stopped.')
        time.sleep(0.5)

        # ── Step 5: Release paddles ────────────────────────────────────────────
        print('\n[5] Releasing duck...')
        sweep(pwms['pl'], 'Left ', LEFT_CLOSED,    LEFT_PREDEPLOY)
        sweep(pwms['pr'], 'Right', RIGHT_CLOSED,   RIGHT_PREDEPLOY)
        time.sleep(0.5)
        print('  Duck released!')

        # ── Step 6: Return to neutral ──────────────────────────────────────────
        print('\n[6] Returning paddles to neutral...')
        sweep(pwms['pl'], 'Left ', LEFT_PREDEPLOY,  LEFT_NEUTRAL)
        sweep(pwms['pr'], 'Right', RIGHT_PREDEPLOY, RIGHT_NEUTRAL)

        print('\nRun test complete!')

    except KeyboardInterrupt:
        print('\nAborted.')
    finally:
        if pwms:
            cleanup(pwms)


if __name__ == '__main__':
    main()

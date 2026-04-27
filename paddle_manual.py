#!/usr/bin/env python3
"""
paddle_manual.py
Control paddle servos manually with keyboard.

Controls:
  W / S  — Left paddle  up / down (2° per press)
  Up / Down arrows — same as W/S for left paddle
  A / D  — Right paddle up / down (2° per press)
  Left / Right arrows — same as A/D for right paddle
  N      — both to neutral (90°)
  Q      — quit

Run on Pi:
  python3 paddle_manual.py
"""

import sys
import tty
import termios
import time

try:
    import RPi.GPIO as GPIO
    HARDWARE = True
except ImportError:
    HARDWARE = False
    print('[WARNING] Simulation mode')

PADDLE_LEFT_PIN  = 23
PADDLE_RIGHT_PIN = 16
SERVO_PWM_FREQ   = 50
NEUTRAL          = 0.0
STEP             = 20.0
ANGLE_MIN        = 0.0
ANGLE_MAX        = 360.0


def angle_to_duty(angle):
    pulse_us = 500 + (angle / 180.0) * 2000
    return (pulse_us / 20000.0) * 100.0


def setup():
    if not HARDWARE:
        return None, None
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)
    GPIO.setup(PADDLE_LEFT_PIN,  GPIO.OUT)
    GPIO.setup(PADDLE_RIGHT_PIN, GPIO.OUT)
    pwm_l = GPIO.PWM(PADDLE_LEFT_PIN,  SERVO_PWM_FREQ)
    pwm_r = GPIO.PWM(PADDLE_RIGHT_PIN, SERVO_PWM_FREQ)
    pwm_l.start(angle_to_duty(NEUTRAL))
    pwm_r.start(angle_to_duty(NEUTRAL))
    return pwm_l, pwm_r


def set_servo(pwm, angle):
    if HARDWARE and pwm:
        pwm.ChangeDutyCycle(angle_to_duty(angle))


def cleanup(pwm_l, pwm_r):
    if not HARDWARE:
        return
    set_servo(pwm_l, NEUTRAL)
    set_servo(pwm_r, NEUTRAL)
    time.sleep(0.3)
    pwm_l.stop()
    pwm_r.stop()
    GPIO.cleanup()


def read_key():
    """Read a keypress — handles regular keys and arrow keys."""
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = sys.stdin.read(1)
        if ch == '\x1b':
            # Arrow key — read two more chars
            ch2 = sys.stdin.read(1)
            ch3 = sys.stdin.read(1)
            if ch2 == '[':
                if ch3 == 'A': return 'UP'
                if ch3 == 'B': return 'DOWN'
                if ch3 == 'C': return 'RIGHT'
                if ch3 == 'D': return 'LEFT'
        return ch
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def clamp(val):
    return max(ANGLE_MIN, min(ANGLE_MAX, val))


def print_status(left, right):
    print(f'\r  Left paddle: {left:6.1f}°  |  Right paddle: {right:6.1f}°    ', end='', flush=True)


def main():
    print('\nPaddle Manual Control')
    print('======================')
    print('  W / Up arrow    — Left paddle +2°')
    print('  S / Down arrow  — Left paddle -2°')
    print('  D / Right arrow — Right paddle +2°')
    print('  A / Left arrow  — Right paddle -2°')
    print('  N               — Both to neutral (90°)')
    print('  Q               — Quit')
    if not HARDWARE:
        print('\n  SIMULATION mode — no GPIO output')

    input('\nPress Enter to start...')

    pwm_l, pwm_r = setup()
    left  = NEUTRAL
    right = NEUTRAL
    print_status(left, right)

    try:
        while True:
            key = read_key()

            if key in ('w', 'W', 'UP'):
                left = clamp(left + STEP)
                set_servo(pwm_l, left)

            elif key in ('s', 'S', 'DOWN'):
                left = clamp(left - STEP)
                set_servo(pwm_l, left)

            elif key in ('d', 'D', 'RIGHT'):
                right = clamp(right + STEP)
                set_servo(pwm_r, right)

            elif key in ('a', 'A', 'LEFT'):
                right = clamp(right - STEP)
                set_servo(pwm_r, right)

            elif key in ('n', 'N'):
                left  = NEUTRAL
                right = NEUTRAL
                set_servo(pwm_l, left)
                set_servo(pwm_r, right)

            elif key in ('q', 'Q', '\x03'):
                break

            print_status(left, right)

    except KeyboardInterrupt:
        pass
    finally:
        print(f'\n\n  Final — Left: {left:.1f}°  Right: {right:.1f}°')
        if pwm_l:
            print('  Parking at neutral...')
            cleanup(pwm_l, pwm_r)
        print('  Done.')


if __name__ == '__main__':
    main()

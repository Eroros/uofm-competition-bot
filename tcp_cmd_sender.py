#!/usr/bin/env python3
"""Simple TCP command sender for robot drive testing.

This script connects to a Pi-side TCP listener and sends one-line JSON
messages with linear/angular velocity fields. It is intended as a quick
transport test before wiring the network stream into ROS or motor control.

Usage examples:
  python tcp_cmd_sender.py --host 100.100.7.54 --port 5005
  python tcp_cmd_sender.py --host 100.100.7.54 --port 5005 --once forward

Interactive commands:
  forward  - send a small forward command
  back     - send a small reverse command
  left     - send a left turn
  right    - send a right turn
  stop     - send zero velocity
  quit     - exit

You can also type raw JSON, for example:
  {"linear": 0.15, "angular": 0.0}
"""

from __future__ import annotations

import argparse
import json
import socket
import sys
import threading
import time
from dataclasses import dataclass

try:
    from inputs import get_gamepad
    INPUTS_AVAILABLE = True
except ImportError:
    INPUTS_AVAILABLE = False


@dataclass
class LastCommand:
    label: str = "none"
    payload: str = ""
    sent_at: float | None = None


def build_payload(command: str) -> tuple[str, str]:
    command = command.strip()
    presets = {
        "forward": {"linear": 0.15, "angular": 0.0},
        "back": {"linear": -0.15, "angular": 0.0},
        "left": {"linear": 0.0, "angular": 0.5},
        "right": {"linear": 0.0, "angular": -0.5},
        "stop": {"linear": 0.0, "angular": 0.0},
    }

    if command in presets:
        payload = presets[command]
        return command, json.dumps(payload, separators=(",", ":"))

    try:
        parsed = json.loads(command)
        if not isinstance(parsed, dict):
            raise ValueError("JSON must be an object")
        linear = float(parsed.get("linear", 0.0))
        angular = float(parsed.get("angular", 0.0))
        payload = {"linear": linear, "angular": angular}
        return "json", json.dumps(payload, separators=(",", ":"))
    except Exception as exc:
        raise ValueError(
            "Unknown command. Use forward/back/left/right/stop/quit or raw JSON."
        ) from exc


def send_line(sock: socket.socket, text: str) -> None:
    sock.sendall((text + "\n").encode("utf-8"))


def gamepad_state_to_payload(state: dict[str, float | bool]) -> str:
    payload = {
        "linear": round(float(state.get("left_stick_y", 0.0)) * 0.15, 3),
        "angular": round(float(state.get("right_stick_x", 0.0)) * 0.5, 3),
    }
    return json.dumps(payload, separators=(",", ":"))


def run_gamepad_reader(sock: socket.socket | None, last: LastCommand, stop_event: threading.Event, local_only: bool) -> int:
    if not INPUTS_AVAILABLE:
        print("inputs library not available; install it with: pip install inputs")
        return 1

    state = {
        "left_stick_y": 0.0,
        "right_stick_x": 0.0,
    }
    prev_payload = None
    last_emit = 0.0

    print("reading gamepad; move the left stick for linear motion and right stick for turn")

    while not stop_event.is_set():
        try:
            events = get_gamepad()
        except Exception as exc:
            print(f"gamepad read error: {exc}")
            time.sleep(0.5)
            continue

        changed = False
        for event in events:
            if event.ev_type == "Absolute":
                norm_val = event.state / 32768.0
                if event.code == "ABS_Y":
                    value = -norm_val
                    if abs(value) < 0.1:
                        value = 0.0
                    state["left_stick_y"] = max(-1.0, min(1.0, value))
                    changed = True
                elif event.code == "ABS_RX":
                    value = norm_val
                    if abs(value) < 0.1:
                        value = 0.0
                    state["right_stick_x"] = max(-1.0, min(1.0, value))
                    changed = True

        now = time.time()
        if changed or now - last_emit >= 0.2:
            payload = gamepad_state_to_payload(state)
            if payload != prev_payload:
                label = "gamepad"
                last.label = label
                last.payload = payload
                last.sent_at = now
                if sock is not None and not local_only:
                    try:
                        send_line(sock, payload)
                        print(f"sent -> {payload}")
                    except OSError as exc:
                        print(f"send failed: {exc}")
                        local_only = True
                        print("switching to local-only mode")
                else:
                    print(f"local-only -> {payload}")
                prev_payload = payload
                last_emit = now

    return 0


def status_loop(last: LastCommand, stop_event: threading.Event) -> None:
    while not stop_event.wait(5.0):
        if last.sent_at is None:
            print("[status] no command sent yet")
            continue

        age = time.time() - last.sent_at
        if age <= 5.0:
            stamp = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(last.sent_at))
            print(f"[status] last sent {age:.1f}s ago at {stamp} -> {last.label}: {last.payload}")
        else:
            print(f"[status] last command is stale ({age:.1f}s old); no send in last 5 sec")


def interactive_client(host: str, port: int, once: str | None) -> int:
    last = LastCommand()
    stop_event = threading.Event()

    try:
        with socket.create_connection((host, port), timeout=5.0) as sock:
            sock.settimeout(1.0)
            print(f"Connected to {host}:{port}")
            print("Type forward/back/left/right/stop, raw JSON, or quit")

            status_thread = threading.Thread(target=status_loop, args=(last, stop_event), daemon=True)
            status_thread.start()

            if once:
                label, payload = build_payload(once)
                send_line(sock, payload)
                last.label = label
                last.payload = payload
                last.sent_at = time.time()
                print(f"sent -> {label}: {payload}")
                stop_event.set()
                return 0

            while True:
                try:
                    line = input("> ").strip()
                except EOFError:
                    line = "quit"

                if not line:
                    continue
                if line.lower() in {"quit", "exit"}:
                    break

                try:
                    label, payload = build_payload(line)
                    send_line(sock, payload)
                    last.label = label
                    last.payload = payload
                    last.sent_at = time.time()
                    print(f"sent -> {label}: {payload}")
                except (ValueError, OSError) as exc:
                    print(f"error: {exc}")

    except OSError as exc:
        print(f"connection failed: {exc}")
        print("running in local test mode; commands will be accepted but not sent")

        status_thread = threading.Thread(target=status_loop, args=(last, stop_event), daemon=True)
        status_thread.start()

        if once:
            label, payload = build_payload(once)
            last.label = label
            last.payload = payload
            last.sent_at = time.time()
            print(f"local-only -> {label}: {payload}")
            stop_event.set()
            return 0

        while True:
            try:
                line = input("> ").strip()
            except EOFError:
                line = "quit"

            if not line:
                continue
            if line.lower() in {"quit", "exit"}:
                break

            try:
                label, payload = build_payload(line)
                last.label = label
                last.payload = payload
                last.sent_at = time.time()
                print(f"local-only -> {label}: {payload}")
            except ValueError as exc:
                print(f"error: {exc}")
    finally:
        stop_event.set()

    return 0


def gamepad_client(host: str, port: int) -> int:
    last = LastCommand()
    stop_event = threading.Event()
    status_thread = threading.Thread(target=status_loop, args=(last, stop_event), daemon=True)
    status_thread.start()

    sock = None
    local_only = False
    try:
        try:
            sock = socket.create_connection((host, port), timeout=5.0)
            sock.settimeout(1.0)
            print(f"Connected to {host}:{port}")
        except OSError as exc:
            print(f"connection failed: {exc}")
            print("running in local test mode; gamepad input will be read but not sent")
            local_only = True

        return run_gamepad_reader(sock, last, stop_event, local_only)
    finally:
        stop_event.set()
        if sock is not None:
            sock.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="TCP test sender for robot commands")
    parser.add_argument("--host", default="100.100.7.54", help="Pi IP or hostname")
    parser.add_argument("--port", type=int, default=5005, help="TCP port on the Pi listener")
    parser.add_argument("--once", default=None, help="Send one command and exit")
    parser.add_argument("--gamepad", action="store_true", help="Read gamepad input and send live commands")
    args = parser.parse_args()

    if args.gamepad:
        return gamepad_client(args.host, args.port)

    return interactive_client(args.host, args.port, args.once)


if __name__ == "__main__":
    raise SystemExit(main())

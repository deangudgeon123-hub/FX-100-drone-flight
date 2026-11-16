#!/usr/bin/env python3
"""Props-off supervised takeoff-sequence validation, NOT a flight controller.
ALL FOUR PROPELLERS MUST BE REMOVED. Run interactively with --run.
Unlock, check status, takeoff pulse, require fresh status 10, then at most
eight seconds of centred commands. ENTER/Ctrl+C, stale replies/status,
unexpected state or timeout trigger best-effort landing. No altitude control.
No guaranteed shutdown during link loss, process death or power failure.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import ipaddress
import json
from pathlib import Path
import select
import sys
import signal
import socket
import time

DRONE = ("192.168.0.1", 50000)
IDLE = bytes.fromhex("68010d8080808020080000000000000024")
UNLOCK = bytes.fromhex("68010d8080808020080400000000000020")

TAKEOFF = bytes.fromhex("68010d808080802008080000000000002c")
LAND = bytes.fromhex("68010d8080808020081000000000000034")


def valid(data, header):
    if len(data) < 4 or data[0] != header or len(data) != data[2] + 4:
        return False
    checksum = 0
    for byte in data[1:-1]:
        checksum ^= byte
    return checksum == data[-1]


class StopRequested(Exception):
    pass


class Link:
    def __init__(self, sock, peer):
        self.sock, self.peer = sock, peer
        self.records = []
        self.counts = Counter()
        self.status = None
        self.status_at = None
        self.start = time.monotonic()
        self.last_reply = None
        self.supervise = False
        self.allowed_states = (0x00, 0x08)

    def has_status(self, value):
        return (self.status == value and self.status_at is not None
                and 0 <= time.monotonic() - self.status_at <= 1.5)

    def record(self, direction, data, address, accepted=None):
        self.records.append({
            "utc": datetime.now(timezone.utc).isoformat(),
            "elapsed": round(time.monotonic() - self.start, 6),
            "direction": direction, "peer": list(address),
            "payload": data.hex(), "valid_reply": accepted,
        })

    def phase(self, label, packet, seconds, hz):
        if packet not in (IDLE, UNLOCK, TAKEOFF, LAND) or not valid(packet, 0x68):
            raise ValueError("Packet not permitted by this bench test")
        print(label, flush=True)
        end = time.monotonic() + seconds
        next_send = time.monotonic()
        while time.monotonic() < end:
            if self.supervise:
                if self.last_reply is None or time.monotonic() - self.last_reply > 1.5:
                    raise StopRequested("Replies stale; attempting LAND")
                if self.status_at is None or time.monotonic() - self.status_at > 1.5:
                    raise StopRequested("Status stale; attempting LAND")
                if self.status not in self.allowed_states:
                    raise StopRequested("Unexpected state; attempting LAND")
                if select.select([sys.stdin], [], [], 0)[0]:
                    sys.stdin.readline()
                    raise StopRequested("ENTER or terminal EOF; attempting LAND")
            if time.monotonic() >= next_send:
                self.sock.sendto(packet, self.peer)
                self.counts["sent"] += 1
                self.record("tx", packet, self.peer)
                next_send = time.monotonic() + 1.0 / hz
            timeout = max(0.0, min(end, next_send, time.monotonic() + 0.05) - time.monotonic())
            if not select.select([self.sock], [], [], timeout)[0]:
                continue
            data, address = self.sock.recvfrom(65535)
            accepted = address == self.peer and valid(data, 0x58)
            self.record("rx", data, address, accepted)
            self.counts["valid_replies" if accepted else "other_replies"] += 1
            if accepted:
                self.last_reply = time.monotonic()
            if accepted and data[:3] == bytes.fromhex("588b0f"):
                self.status_at = time.monotonic()
                state = data[12]
                if state != self.status:
                    print(f"  Observed status byte 12: {state:02x}", flush=True)
                    self.status = state


def sequence(link):
    attempted = False
    try:
        link.phase("Checking initial status for 2 seconds...", IDLE, 2, 1)
        if not link.has_status(0x00):
            print("No fresh initial 00 status. No unlock sent.")
            return
        link.supervise = True
        attempted = True
        link.phase("UNLOCK: ENTER at any time requests landing.", UNLOCK, 1, 50)
        link.phase("Checking unlock response...", IDLE, 2, 1)
        if not link.has_status(0x08):
            raise StopRequested("Unlock not confirmed; attempting LAND")
        link.allowed_states = (0x08, 0x10)
        takeoff_started = time.monotonic()
        link.phase("TAKEOFF pulse; ENTER requests LAND.", TAKEOFF, 1, 50)
        if not link.has_status(0x10) or link.status_at < takeoff_started:
            raise StopRequested("Fresh takeoff status 10 not confirmed; attempting LAND")
        link.allowed_states = (0x10,)
        link.phase("Centred controls for up to 8 seconds. ENTER requests LAND.", IDLE, 8, 1)
        print("Fixed time limit reached; attempting LAND.")
    except (StopRequested, KeyboardInterrupt) as error:
        print(str(error) or "Ctrl+C: attempting LAND")
    finally:
        link.supervise = False
        if attempted:
            # Keep a second Ctrl+C from interrupting this bounded landing attempt.
            previous = signal.signal(signal.SIGINT, signal.SIG_IGN)
            try:
                link.phase("LAND attempt (not guaranteed motor shutdown)...", LAND, 1, 50)
                link.phase("Monitoring for 5 seconds; check motors physically.", IDLE, 5, 1)
            finally:
                signal.signal(signal.SIGINT, previous)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()
    if not args.run:
        print(__doc__)
        print("With ALL propellers removed: python3 ~/fx100_supervised_bench_8s.py --run")
        return
    print("ALL PROPELLERS MUST BE REMOVED. Keep the drone on a stable surface.")
    print("Close the phone app and other Pi senders. Have access to the battery.")
    print("Takeoff-sequence bench validation. ENTER requests LAND; automatic timeout also lands.")
    print("If landing does not stop them, disconnect the battery safely.")
    if not sys.stdin.isatty():
        raise OSError("Run in an interactive SSH terminal")
    if input("Type PROPS OFF to begin: ").strip() != "PROPS OFF":
        print("Cancelled. No packets sent.")
        return
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as route:
        route.connect(DRONE)
        local_ip = route.getsockname()[0]
    if ipaddress.ip_address(local_ip) not in ipaddress.ip_network("192.168.0.0/24") or local_ip == DRONE[0]:
        raise OSError(f"Route uses {local_ip}; connect the Pi to the drone network first")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
    path = Path.home() / f"fx100_supervised_bench_8s_{stamp}.jsonl"
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind((local_ip, 5010))
        # Open the log before transmitting; buffer records during motor actions
        # so a disk-write failure cannot interrupt the landing pulse.
        with path.open("x", encoding="utf-8") as log:
            link = Link(sock, DRONE)
            print(f"Using {local_ip}:5010 -> {DRONE[0]}:{DRONE[1]}")
            try:
                sequence(link)
            except (KeyboardInterrupt, OSError) as error:
                print(f"Test interrupted ({type(error).__name__}). Check the motors physically.")
            finally:
                for record in link.records:
                    log.write(json.dumps(record) + "\n")
                print("Counts:", dict(link.counts))
                print("Log:", path)
                print("No automatic confirmation of motor shutdown is provided.")
                print("Disconnect the drone battery after the test.")


if __name__ == "__main__":
    try:
        main()
    except (OSError, EOFError, KeyboardInterrupt) as error:
        print(f"Stopped: {type(error).__name__}. If motors are running, disconnect the battery safely.")
        raise SystemExit(1)

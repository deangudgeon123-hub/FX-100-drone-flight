#!/usr/bin/env python3
"""Props-off FX100 unlock/landing bench test; NOT a flight controller.

Uses the exact packets correlated with the user's 11 Nov 2026 app actions.
No takeoff packet, axis movement, or auxiliary startup packet is sent.
Default invocation describes the test. Use --run to perform it.
Ctrl+C after an unlock attempt triggers a best-effort landing sequence;
this is NOT a guaranteed emergency stop. Disconnect the battery if needed.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import ipaddress
import json
from pathlib import Path
import select
import socket
import time

DRONE = ("192.168.0.1", 50000)
IDLE = bytes.fromhex("68010d8080808020080000000000000024")
UNLOCK = bytes.fromhex("68010d8080808020080400000000000020")
LAND = bytes.fromhex("68010d8080808020081000000000000034")


def valid(data, header):
    if len(data) < 4 or data[0] != header or len(data) != data[2] + 4:
        return False
    checksum = 0
    for byte in data[1:-1]:
        checksum ^= byte
    return checksum == data[-1]


class Link:
    def __init__(self, sock, peer):
        self.sock, self.peer = sock, peer
        self.records = []
        self.counts = Counter()
        self.status = None
        self.start = time.monotonic()

    def record(self, direction, data, address, accepted=None):
        self.records.append({
            "utc": datetime.now(timezone.utc).isoformat(),
            "elapsed": round(time.monotonic() - self.start, 6),
            "direction": direction, "peer": list(address),
            "payload": data.hex(), "valid_reply": accepted,
        })

    def phase(self, label, packet, seconds, hz):
        if packet not in (IDLE, UNLOCK, LAND) or not valid(packet, 0x68):
            raise ValueError("Packet not permitted by this bench test")
        print(label, flush=True)
        end = time.monotonic() + seconds
        next_send = time.monotonic()
        while time.monotonic() < end:
            if time.monotonic() >= next_send:
                self.sock.sendto(packet, self.peer)
                self.counts["sent"] += 1
                self.record("tx", packet, self.peer)
                next_send = time.monotonic() + 1.0 / hz
            timeout = max(0.0, min(end, next_send) - time.monotonic())
            if not select.select([self.sock], [], [], timeout)[0]:
                continue
            data, address = self.sock.recvfrom(65535)
            accepted = address == self.peer and valid(data, 0x58)
            self.record("rx", data, address, accepted)
            self.counts["valid_replies" if accepted else "other_replies"] += 1
            if accepted and data[:3] == bytes.fromhex("588b0f"):
                state = data[12]
                if state != self.status:
                    print(f"  Observed status byte 12: {state:02x}", flush=True)
                    self.status = state


def sequence(link):
    attempted = False
    try:
        before = link.counts["valid_replies"]
        link.phase("Checking replies for 2 seconds...", IDLE, 2, 1)
        if link.counts["valid_replies"] == before:
            print("No valid replies. Unlock will NOT be sent.")
            return
        attempted = True
        link.phase("UNLOCK pulse: watch for slow motor rotation...", UNLOCK, 1, 50)
        link.phase("Centred controls for 2 seconds...", IDLE, 2, 1)
    finally:
        if attempted:
            # Best effort only: link/power/process failure can prevent delivery.
            link.phase("LAND pulse: watch whether the motors stop...", LAND, 1, 50)
            link.phase("Watching replies for 5 more seconds...", IDLE, 5, 1)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true")
    args = parser.parse_args()
    if not args.run:
        print(__doc__)
        print("With ALL propellers removed: python3 ~/fx100_unlock_test.py --run")
        return
    print("ALL PROPELLERS MUST BE REMOVED. Keep the drone on a stable surface.")
    print("Close the phone app and other Pi senders. Have access to the battery.")
    print("This test may start the motors. No takeoff command will be sent.")
    print("If landing does not stop them, disconnect the battery safely.")
    if input("Type PROPS OFF to begin: ").strip() != "PROPS OFF":
        print("Cancelled. No packets sent.")
        return
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as route:
        route.connect(DRONE)
        local_ip = route.getsockname()[0]
    if ipaddress.ip_address(local_ip) not in ipaddress.ip_network("192.168.0.0/24") or local_ip == DRONE[0]:
        raise OSError(f"Route uses {local_ip}; connect the Pi to the drone network first")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
    path = Path.home() / f"fx100_unlock_{stamp}.jsonl"
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

#!/usr/bin/env python3
"""FX100 propeller-free link probe. Python standard library only.

Default: explain the test; no network traffic. --probe: send the exact captured
initial centred-stick packet at 1 Hz for five seconds, from UDP port 5010.
No takeoff, landing, disarming, calibration or unknown setup packets are sent.
Centred-stick packets are NOT a verified motor-stop or hover command.
See FINDINGS.md for evidence and limitations. This is not a flight controller.
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
INITIAL = bytes.fromhex("68010d8080808020080000000000000024")


def valid_frame(data, header):
    if len(data) < 4 or data[0] != header or len(data) != data[2] + 4:
        return False
    check = 0
    for value in data[1:-1]:
        check ^= value
    return check == data[-1]


def probe(sock, peer, log, duration=5.0):
    """Bounded synchronous sender/receiver; log every received datagram.

    No catch-up bursts after a scheduling delay. RX validity only means a
    correctly framed reply, never acceptance of a flight command.
    """
    started = time.monotonic()
    deadline = started + duration
    next_send = started
    counts = Counter()
    types = Counter()

    def record(direction, data, address, accepted=None):
        log.write(json.dumps({
            "utc": datetime.now(timezone.utc).isoformat(),
            "elapsed": round(time.monotonic() - started, 6),
            "direction": direction, "peer": list(address),
            "payload": data.hex(), "valid_reply": accepted,
        }) + "\n")
        log.flush()

    try:
        while time.monotonic() < deadline:
            now = time.monotonic()
            if now >= next_send:
                sock.sendto(INITIAL, peer)
                counts["tx"] += 1
                record("tx", INITIAL, peer)
                next_send = time.monotonic() + 1.0
            timeout = max(0.0, min(next_send, deadline) - time.monotonic())
            ready, _, _ = select.select([sock], [], [], timeout)
            if not ready:
                continue
            data, address = sock.recvfrom(65535)
            accepted = address == peer and valid_frame(data, 0x58)
            record("rx", data, address, accepted)
            if accepted:
                counts["valid_rx"] += 1
                types[f"58 {data[1]:02x} {data[2]:02x}"] += 1
            else:
                counts["other_rx"] += 1
    except KeyboardInterrupt:
        counts["interrupted"] += 1
        print("Interrupted. Transmission ended; this does not disarm the drone.")
    return dict(counts), dict(types)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--probe", action="store_true", help="run the five-second props-off link test")
    args = parser.parse_args()
    if not args.probe:
        print(__doc__)
        print("After removing ALL propellers: python3 fx100_probe.py --probe")
        return 0

    print("BENCH TEST ONLY. Remove every propeller and place the drone on a stable surface.")
    print("Close the phone control app and other Pi sender scripts first.")
    print("This tests replies, not takeoff. Ctrl+C stops sending; it is NOT a motor stop.")
    print("If motors move unexpectedly, disconnect the drone battery safely.")
    if input("Type PROPS OFF to begin: ").strip() != "PROPS OFF":
        print("Cancelled. No packets sent.")
        return 1

    # UDP connect selects the local route; it sends no application datagram.
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as route:
        route.connect(DRONE)
        local_ip = route.getsockname()[0]
    if ipaddress.ip_address(local_ip) not in ipaddress.ip_network("192.168.0.0/24") or local_ip == DRONE[0]:
        print(f"Route uses {local_ip}, not a drone-network client address. No packets sent.")
        return 2

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S_%fZ")
    log_path = Path.home() / f"fx100_probe_{stamp}.jsonl"
    assert valid_frame(INITIAL, 0x68)
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        try:
            sock.bind((local_ip, 5010))
        except OSError as error:
            print(f"Cannot bind {local_ip}:5010: {error}. No packets sent.")
            return 2
        with log_path.open("x", encoding="utf-8") as log:
            print(f"Testing {local_ip}:5010 -> {DRONE[0]}:{DRONE[1]} for 5 seconds...", flush=True)
            counts, types = probe(sock, DRONE, log)

    print(f"Sent: {counts.get('tx', 0)}")
    print(f"Valid replies from drone: {counts.get('valid_rx', 0)}")
    print(f"Other/invalid replies: {counts.get('other_rx', 0)}")
    for kind, count in sorted(types.items()):
        print(f"  {kind}: {count}")
    print(f"Log: {log_path}")
    print("Transmission ended. This is not confirmation that motors are disarmed.")
    print("Disconnect the drone battery after this bench test.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, EOFError) as error:
        print(f"Test stopped: {error}. No motor-stop command has been sent.")
        raise SystemExit(2)

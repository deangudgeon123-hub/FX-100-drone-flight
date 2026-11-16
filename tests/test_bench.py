"""Offline checks only: no real network or motor activity."""
import contextlib
import importlib.util
import io
from pathlib import Path
import time
import unittest
from unittest.mock import patch

path = Path(__file__).resolve().parents[1] / 'scripts/fx100_supervised_bench_8s.py'
spec = importlib.util.spec_from_file_location('bench', path)
bench = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bench)

class FakeLink:
    def __init__(self, mode):
        self.mode = mode
        self.calls = []
        self.status_at = time.monotonic()
    def has_status(self, value):
        return not ((self.mode == 'initial' and value == 0) or
                    (self.mode == 'unlock' and value == 8) or
                    (self.mode == 'takeoff' and value == 16))
    def phase(self, label, packet, seconds, hz):
        self.calls.append((label, packet, seconds, hz))
        self.status_at = time.monotonic()
        if packet == bench.TAKEOFF and self.mode == 'interrupt':
            raise KeyboardInterrupt()
        if label.startswith('Centred') and self.mode in ('manual', 'stale'):
            raise bench.StopRequested(self.mode)

class BenchTests(unittest.TestCase):
    def run_case(self, mode):
        link = FakeLink(mode)
        with patch.object(bench.socket, 'socket', side_effect=AssertionError('Network forbidden')), contextlib.redirect_stdout(io.StringIO()):
            bench.sequence(link)
        return link.calls
    def test_frames_and_corruption(self):
        for packet in (bench.IDLE, bench.UNLOCK, bench.TAKEOFF, bench.LAND):
            self.assertTrue(bench.valid(packet, 0x68))
            corrupt = bytearray(packet); corrupt[4] ^= 1
            self.assertFalse(bench.valid(corrupt, 0x68))
            self.assertFalse(bench.valid(packet[:-1], 0x68))
            self.assertFalse(bench.valid(packet, 0x58))
    def test_no_initial_status_no_unlock(self):
        calls = self.run_case('initial')
        self.assertTrue(all(p == bench.IDLE for _, p, _, _ in calls))
    def test_unlock_gate(self):
        calls = self.run_case('unlock')
        self.assertNotIn(bench.TAKEOFF, [p for _, p, _, _ in calls])
        self.assertIn(bench.LAND, [p for _, p, _, _ in calls])
    def test_takeoff_gate(self):
        self.assertFalse(any(label.startswith('Centred') for label, *_ in self.run_case('takeoff')))
    def test_landing_cleanup(self):
        for mode in ('normal', 'manual', 'stale', 'interrupt', 'takeoff'):
            with self.subTest(mode=mode):
                self.assertIn(bench.LAND, [p for _, p, _, _ in self.run_case(mode)])
    def test_eight_second_interval(self):
        centred = [c for c in self.run_case('normal') if c[0].startswith('Centred')]
        self.assertEqual([(p,s,hz) for _,p,s,hz in centred], [(bench.IDLE,8,1)])

if __name__ == '__main__':
    unittest.main()

#!/usr/bin/env python3
"""Tests for the host-allocation log aggregator."""
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wol_hostmmap_report import aggregate, parse, totals  # noqa: E402

SAMPLE = """\
HOSTMMAP ts=100 op=mmap pid=7 size=75497472 prot=0x3 flags=0x22 fd=-1 off=0 ret=(nil) frames=wol-horizon+0x111;libc.so.6+0x222;
HOSTMMAP ts=200 op=malloc pid=7 size=16777216 ret=(nil) frames=wol-horizon+0x333;
HOSTMMAP ts=300 op=mmap pid=9 size=75497472 prot=0x3 flags=0x22 fd=-1 off=0 ret=(nil) frames=sh+0x444;
HOSTMMAP ts=400 op=munmap pid=7 size=50331648 ret=0x7f00000000 frames=wol-horizon+0x555;
HOSTMMAP garbage line
"""


class ReportTest(unittest.TestCase):
    def test_parse_skips_garbage(self):
        self.assertEqual(len(parse(SAMPLE)), 4)

    def test_totals_per_pid(self):
        self.assertEqual(totals(parse(SAMPLE))["by_op"], {"mmap": 2, "malloc": 1, "munmap": 1})
        self.assertEqual(totals(parse(SAMPLE), 7)["requests"], 3)

    def test_aggregate_groups_and_orders(self):
        rows = aggregate(parse(SAMPLE))
        self.assertEqual(rows[0]["size"], 75497472)
        self.assertEqual(rows[0]["count"], 2)
        self.assertEqual(rows[0]["pids"], [7, 9])
        self.assertEqual(rows[0]["first_frames"], ["wol-horizon+0x111", "libc.so.6+0x222"])
        self.assertEqual(rows[0]["first_extra"], "prot=0x3 flags=0x22 fd=-1 off=0")

    def test_pid_filter(self):
        rows = aggregate(parse(SAMPLE), 7)
        self.assertEqual([r["size"] for r in rows], [75497472, 50331648, 16777216])


if __name__ == "__main__":
    unittest.main()

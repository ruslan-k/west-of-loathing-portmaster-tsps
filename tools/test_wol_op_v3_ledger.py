#!/usr/bin/env python3
"""Data-free tests for the WOL_OP_V3 ledger contract (synthetic log lines)."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wol_op_v3_ledger import parse, summarize, validate


def row(frame, cls, n, sum_wall, sum_cpu=0.0, tid=1, mean_wall=None, mean_cpu=None):
    mean_wall = sum_wall / n if mean_wall is None else mean_wall
    mean_cpu = sum_cpu / n if mean_cpu is None else mean_cpu
    return ("WOL_OP_V3 frame=%d tid=%d cls=%s n=%d sum_wall_ms=%.3f sum_cpu_ms=%.3f "
            "mean_wall_ms=%.3f mean_cpu_ms=%.3f" % (frame, tid, cls, n, sum_wall, sum_cpu, mean_wall, mean_cpu))


def window(frame, elapsed, replay=20.0, count=60):
    return ("NVN_PROFILE frame=%d count=%d elapsed-ms=%.3f replay-ms=%.3f present-ms=1.700 "
            "readback-ms=0.000 scope=wall-time-per-frame" % (frame, count, elapsed, replay))


class LedgerTests(unittest.TestCase):
    def test_empty_log_is_not_a_failure(self):
        _, rows = parse([window(60, 40.0)])
        self.assertEqual(rows, [])
        self.assertEqual(validate(rows), [])

    def test_mixed_classes_in_one_frame(self):
        rows = parse([row(7, "DrawArrays", 3, 6.0), row(7, "ReportCounter", 2, 7.0)])[1]
        self.assertEqual(validate(rows), [])
        s = summarize([], rows)
        self.assertEqual(s["v3"]["frames"], 1)
        self.assertEqual(round(s["v3"]["accounted_ms_median"], 3), 13.0)

    def test_frame_rollover_must_increase(self):
        self.assertEqual(validate(parse([row(7, "DrawArrays", 3, 6.0), row(8, "DrawArrays", 3, 6.0)])[1]), [])
        problems = validate(parse([row(8, "DrawArrays", 3, 6.0), row(7, "DrawArrays", 3, 6.0)])[1])
        self.assertTrue(any("after" in p for p in problems))

    def test_duplicate_row_is_rejected(self):
        problems = validate(parse([row(7, "DrawArrays", 3, 6.0), row(7, "DrawArrays", 3, 6.0)])[1])
        self.assertTrue(any("duplicate" in p for p in problems))

    def test_worker_threads_are_separate_owners(self):
        rows = parse([row(7, "DrawArrays", 3, 6.0, tid=1), row(7, "DrawArrays", 3, 5.0, tid=2)])[1]
        self.assertEqual(validate(rows), [])
        self.assertEqual(sorted(summarize([], rows)["tids"]), [1, 2])

    def test_terminal_partial_bucket_is_legal(self):
        rows = parse([row(7, "DrawArrays", 3, 6.0), row(7, "ReportCounter", 2, 7.0),
                      row(8, "DrawArrays", 1, 2.0)])[1]
        self.assertEqual(validate(rows), [])
        self.assertEqual(summarize([], rows)["v3"]["frames"], 2)

    def test_unit_math_is_checked(self):
        ok = parse([row(7, "DrawArrays", 4, 10.0, 8.0)])[1]
        self.assertEqual(validate(ok), [])
        bad = parse([row(7, "DrawArrays", 4, 9.0, 8.0, mean_wall=2.5)])[1]
        self.assertTrue(any("mean*n" in p for p in validate(bad)))

    def test_accounted_share_uses_matched_windows(self):
        rows = parse([row(7, "DrawArrays", 3, 6.0), row(7, "ReportCounter", 2, 6.0)])[1]
        s = summarize(parse([window(60, 40.0)])[0], rows)
        self.assertEqual(s["v3"]["accounted_pct_of_frame"], 30.0)


if __name__ == "__main__":
    unittest.main()

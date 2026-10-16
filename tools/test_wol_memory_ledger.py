#!/usr/bin/env python3
"""Data-free tests at the ledger parser/collector interface (roadmap §6/§10)."""
import tempfile
import unittest
from pathlib import Path


class LedgerTests(unittest.TestCase):
    def test_mali_commit_uses_hex_commit_column_not_virtual_size(self):
        from wol_memory_ledger import parse_mali
        sample = ('Zone name: SAME_VA:\n'
                  ': VA, VA size, Commit size, Flags, Mem type\n'
                  '10000000, 8000, 3000, c07e, Native\n'
                  '20000000, 10000, 2000, c07e, Native\n')
        self.assertEqual(parse_mali(sample), {'allocations': 2, 'virtual_bytes': 98304,
                                            'commit_bytes': 20480})

    def test_unavailable_gpu_is_not_zero(self):
        from wol_memory_ledger import mali_contexts
        with tempfile.TemporaryDirectory() as d:
            result = mali_contexts(Path(d)/'missing', 123)
        self.assertFalse(result['available'])
        self.assertIsNone(result['commit_bytes'])

    def test_only_exact_pid_contexts_are_included(self):
        from wol_memory_ledger import mali_contexts
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            for name in ('123_1', '123_2', '1234_1', 'defaults'):
                (root/name).mkdir()
                (root/name/'mem_allocs').write_text('10000000, 8000, 1000, c07e, Native\n')
            result = mali_contexts(root, 123)
        self.assertEqual(result['commit_bytes'], 8192)
        self.assertEqual(len(result['contexts']), 2)

    def test_frame_intervals_are_not_thresholded_or_profile_span_fps(self):
        from wol_memory_ledger import frame_stats
        result = frame_stats('MOMO_FRAME frame=7 ns=1000000000\n'
                             'MOMO_FRAME frame=8 ns=1020000000\n'
                             'MOMO_FRAME frame=9 ns=1060000000\n')
        self.assertAlmostEqual(result['presents_per_s'], 100/3)
        self.assertEqual(result['p50_ms'], 30)
        self.assertEqual(result['p95_ms'], 39)
        self.assertEqual(result['intervals'], 2)
        with self.assertRaises(ValueError):
            frame_stats('MOMO_FRAME frame=7 ns=100\nMOMO_FRAME frame=9 ns=200\n')

    def test_identity_change_refuses_torn_sample(self):
        from wol_memory_ledger import coherent
        with self.assertRaises(RuntimeError):
            coherent({'start_ticks': 1}, {'start_ticks': 2})


if __name__ == '__main__':
    unittest.main()

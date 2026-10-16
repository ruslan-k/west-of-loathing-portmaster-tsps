#!/usr/bin/env python3
"""Contract tests; byte fixtures are synthetic, never claimed as device evidence."""
import importlib.util
from pathlib import Path
import struct
import unittest

PATH = Path(__file__).with_name('wol_memory_profile.py')

class ProfileTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if PATH.exists():
            spec = importlib.util.spec_from_file_location('profile_wol', PATH)
            assert spec and spec.loader
            cls.m = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(cls.m)
        else:
            cls.m = None

    def module(self):
        self.assertIsNotNone(self.m, 'read-only profiler has not been implemented')
        assert self.m is not None
        return self.m

    def test_pagemap_classifies_without_reading_page_contents(self):
        m = self.module()
        entries = [1 << 63, 1 << 62, 0, (1 << 63) | (1 << 55)]
        self.assertEqual(m.page_counts(struct.pack('<4Q', *entries)),
                         {'present': 2, 'swapped': 1, 'unmapped': 1, 'soft_dirty': 1})

    def test_pool_union_is_not_added_twice(self):
        m = self.module()
        self.assertEqual(m.union_size([(0, 8192), (4096, 12288), (16384, 20480)]), 16384)
        self.assertEqual(m.union_size([]), 0)

    def test_smaps_preserves_status_disagreement(self):
        m = self.module()
        maps = m.parse_smaps('1000-3000 rw-p 00000000 00:00 0\nSize: 8 kB\nPss: 4 kB\nSwapPss: 2 kB\n')
        self.assertEqual(maps[0]['Pss'], 4)
        self.assertEqual(maps[0]['SwapPss'], 2)
        self.assertEqual(maps[0]['start'], 4096)

    def test_layout_must_match_exact_executable(self):
        m = self.module()
        with self.assertRaises(ValueError):
            m.require_elf({'elf_sha256': 'a' * 64}, 'b' * 64)

    def test_lifetime_uses_ids_not_reused_object_addresses(self):
        m = self.module()
        a = {'textures': [{'id': 1, 'object': 10}], 'pools': []}
        b = {'textures': [{'id': 2, 'object': 10}], 'pools': []}
        delta = m.lifecycle(a, b)
        self.assertEqual(delta['created_texture_ids'], [2])
        self.assertEqual(delta['finalized_texture_ids'], [1])

    def test_platform_snapshot_has_online_mask_and_clock_map(self):
        m = self.module()
        state = m.platform_state()
        self.assertIn('online_cpus', state)
        self.assertIsInstance(state['clocks'], dict)

    def test_no_free_page_claim_from_pagemap(self):
        m = self.module()
        self.assertNotIn('free', m.page_counts(struct.pack('<Q', 0)))

if __name__ == '__main__':
    unittest.main()

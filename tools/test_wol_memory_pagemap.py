"""Synthetic pagemap accounting; no fixture is device evidence."""
import struct
import unittest
from wol_pagemap_attribution import account_pages

PRESENT = 1 << 63
SWAPPED = 1 << 62


def raw(*entries):
    return struct.pack('<' + 'Q' * len(entries), *entries)


class PagemapAttributionTests(unittest.TestCase):
    def test_aliases_are_deduplicated_without_assigning_first_owner(self):
        chunks = [('anon', raw(PRESENT | 7, PRESENT | 9)),
                  ('romfs', raw(PRESENT | 7))]
        a = account_pages(chunks)
        b = account_pages(reversed(chunks))
        self.assertEqual(a, b)
        self.assertEqual(a['totals']['present_pages'], 3)
        self.assertEqual(a['totals']['unique_present_pages'], 2)
        self.assertEqual(a['totals']['resident_repeat_pages'], 1)
        self.assertEqual(a['resident_owner_groups'], {'anon': 1, 'anon|romfs': 1})

    def test_swap_identity_uses_type_and_offset(self):
        same = SWAPPED | (5 << 5) | 2
        different_type = SWAPPED | (5 << 5) | 3
        a = account_pages([('anon', raw(same, different_type)), ('romfs', raw(same))])
        self.assertEqual(a['totals']['swapped_pages'], 3)
        self.assertEqual(a['totals']['unique_swap_pages'], 2)
        self.assertEqual(a['totals']['swap_repeat_pages'], 1)
        self.assertEqual(a['swap_owner_groups'], {'anon': 1, 'anon|romfs': 1})

    def test_hidden_pfns_are_unknown_not_one_shared_physical_page(self):
        a = account_pages([('anon', raw(PRESENT, PRESENT, 0))])
        self.assertFalse(a['resident_dedup_available'])
        self.assertIsNone(a['totals']['unique_present_pages'])
        self.assertIsNone(a['totals']['resident_repeat_pages'])
        self.assertEqual(a['totals']['unknown_pfn_pages'], 2)
        self.assertEqual(a['totals']['unmapped_pages'], 1)

    def test_partial_hidden_pfns_do_not_produce_a_complete_total(self):
        a = account_pages([('anon', raw(PRESENT, PRESENT | 9))])
        self.assertFalse(a['resident_dedup_available'])
        self.assertEqual(a['totals']['known_unique_present_pages'], 1)
        self.assertIsNone(a['totals']['unique_present_pages'])

    def test_truncated_entries_are_refused(self):
        with self.assertRaises(ValueError):
            account_pages([('anon', b'\0' * 7)])

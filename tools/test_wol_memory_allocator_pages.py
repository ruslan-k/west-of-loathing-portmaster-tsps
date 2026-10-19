import io
import struct
import unittest
from wol_allocator_pages import AllocationCoverage, classify_pages


class AllocatorPageAccounting(unittest.TestCase):
    def test_freed_reused_and_unseen_pages_are_disjoint(self):
        c=AllocationCoverage(0x1000,0x6000,page_size=4096)
        c.feed('WOL_ALLOC event=alloc ptr=0x1000 bytes=0x3000 seq=0x1 incomplete=0x0')
        c.feed('WOL_ALLOC event=free ptr=0x1000 bytes=0x3000 seq=0x2 incomplete=0x0')
        c.feed('WOL_ALLOC event=alloc ptr=0x2000 bytes=0x1000 seq=0x3 incomplete=0x0')
        # pages: historical-only, live, historical-only, never-seen, never-seen
        values=[1<<62,1<<63,1<<62,1<<63,0]
        result=classify_pages(c,io.BytesIO(struct.pack('<5Q',*values)))
        self.assertEqual(result['classes']['live'],dict(pages=1,present=1,swapped=0))
        self.assertEqual(result['classes']['historical_not_live'],dict(pages=2,present=0,swapped=2))
        self.assertEqual(result['classes']['unseen'],dict(pages=2,present=1,swapped=0))
        self.assertFalse(result['trace_incomplete'])
        self.assertFalse(result['reclaim_safe'])
    def test_partial_pages_count_once_and_cap_is_detected(self):
        c=AllocationCoverage(0x1000,0x4000)
        c.feed('WOL_ALLOC event=alloc ptr=0x1001 bytes=0xfff seq=0x1 incomplete=0x0')
        c.feed('WOL_ALLOC event=alloc ptr=0x1800 bytes=0x1000 seq=0x2 incomplete=0x0')
        c.feed('WOL_ALLOC event=alloc ptr=0x3000 bytes=0x1 seq=0x4 incomplete=0x1')
        result=classify_pages(c,io.BytesIO(struct.pack('<3Q',*[1<<62]*3)))
        self.assertEqual(result['classes']['live']['swapped'],3)
        self.assertTrue(result['trace_incomplete'])
    def test_crossing_bounds_clips_and_short_pagemap_is_error(self):
        c=AllocationCoverage(0x2000,0x4000)
        c.feed('WOL_ALLOC event=alloc ptr=0x1000 bytes=0x2001 seq=0x1 incomplete=0x0')
        result=classify_pages(c,io.BytesIO(struct.pack('<2Q',1<<63,1<<62)))
        self.assertEqual(result['classes']['live'],dict(pages=2,present=1,swapped=1))
        with self.assertRaisesRegex(ValueError,'short pagemap'):
            classify_pages(c,io.BytesIO(b'\0'*8))
    def test_unmatched_free_and_duplicate_live_refuse_completeness(self):
        c=AllocationCoverage(0x1000,0x5000)
        c.feed('WOL_ALLOC event=free ptr=0x1000 bytes=0x1000 seq=0x1 incomplete=0x0')
        c.feed('WOL_ALLOC event=alloc ptr=0x1000 bytes=0x1000 seq=0x2 incomplete=0x0')
        c.feed('WOL_ALLOC event=alloc ptr=0x1000 bytes=0x2000 seq=0x3 incomplete=0x0')
        self.assertTrue(c.incomplete)


if __name__=='__main__':unittest.main()

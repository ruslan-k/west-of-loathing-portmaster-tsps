import tempfile
import unittest
from pathlib import Path
from wol_roadmap_probe import aggregate_callers, decode_pagemap, live_blocks, scan_log, trace_threshold

class BlockPages(unittest.TestCase):
    def test_live_blocks_matches_frees_bounds_and_callers(self):
        t='\n'.join([
            'WOL_ALLOC event=alloc ptr=0x1000 bytes=0x100 caller=main+0x1 seq=0x1',
            'WOL_ALLOC event=alloc ptr=0x2000 bytes=0x800000 caller=main+0x2 seq=0x2',
            'WOL_ALLOC event=alloc ptr=0x4000 bytes=0x4000000 caller=main+0x3 seq=0x3',
            'WOL_ALLOC event=free ptr=0x4000 bytes=0x4000000 seq=0x4',
            'WOL_ALLOC event=realloc ptr=0x2000 bytes=0x900000 caller=main+0x4 seq=0x5',
            'unrelated line'])
        self.assertEqual(live_blocks(t),[ (0x2000,0x900000,'main+0x4') ])
        self.assertEqual(live_blocks(t,min_bytes=0x800001),[ (0x2000,0x900000,'main+0x4') ])
        self.assertEqual(live_blocks(t,min_bytes=0x100),[ (0x2000,0x900000,'main+0x4'),(0x1000,0x100,'main+0x1') ])
        self.assertEqual(live_blocks(''),[])
    def test_pagemap_bits_present_swapped_file_exclusive(self):
        def entry(present=False,swapped=False,file_=False,exclusive=False):
            v=0
            v|=int(present)<<63;v|=int(swapped)<<62;v|=int(file_)<<61;v|=int(exclusive)<<60
            return v.to_bytes(8,'little')
        data=entry(present=True,exclusive=True)+entry(swapped=True)+entry(present=True,file_=True)+entry()
        self.assertEqual(decode_pagemap(data),dict(pages=4,present=2,swapped=1,file_or_shared=1,exclusive=1))
        with self.assertRaises(ValueError):decode_pagemap(b'x'*7)
    def test_trace_threshold_reads_header_and_bounds(self):
        self.assertEqual(trace_threshold('WOL_ALLOC_TRACE enabled=1 threshold=262144 slots=2048 events=8192 scope=SDK'),262144)
        self.assertEqual(trace_threshold('no header here'),4*1024*1024)
        self.assertEqual(trace_threshold('WOL_ALLOC_TRACE enabled=1 threshold=123 slots=x'),4*1024*1024)
        self.assertEqual(trace_threshold('WOL_ALLOC_TRACE enabled=1 threshold=99999999999999 slots=x'),4*1024*1024)
    def test_scan_log_streams_blocks_with_log_threshold(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'latest.log'
            p.write_text('\n'.join([
                'noise',
                'WOL_ALLOC_TRACE enabled=1 threshold=262144 slots=2048 events=8192 scope=SDK',
                'WOL_ALLOC event=alloc ptr=0x10000 bytes=0x40000 caller=main+0x5 seq=0x1',
                'WOL_ALLOC event=alloc ptr=0x80000 bytes=0x10000 caller=main+0x6 seq=0x2',
                'WOL_ALLOC event=free ptr=0x80000 bytes=0x10000 seq=0x3']))
            blocks,threshold=scan_log(p)
            self.assertEqual(threshold,262144)
            self.assertEqual(blocks,[ (0x10000,0x40000,'main+0x5') ])
            p.write_text('WOL_ALLOC event=alloc ptr=0x2000 bytes=0x200000 caller=main+0x7 seq=0x1\n')
            blocks,threshold=scan_log(p)
            self.assertEqual(threshold,4*1024*1024)
            self.assertEqual(blocks,[])
    def test_aggregate_callers_sums_and_sorts_by_swap(self):
        samples=[
            dict(ptr='0x1',requested_kib=512,present_kib=300,swapped_kib=200,caller='a+0x1'),
            dict(ptr='0x2',requested_kib=256,present_kib=100,swapped_kib=150,caller='a+0x1'),
            dict(ptr='0x3',requested_kib=1024,present_kib=900,swapped_kib=100,caller='b+0x2'),
            dict(ptr='0x4',requested_kib=64,error='short read',caller='c+0x3')]
        rows=aggregate_callers(samples)
        self.assertEqual([r['caller'] for r in rows],['a+0x1','b+0x2'])
        self.assertEqual(rows[0],dict(caller='a+0x1',blocks=2,requested_kib=768,present_kib=400,swapped_kib=350))

if __name__=='__main__':unittest.main()

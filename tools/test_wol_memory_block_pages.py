import unittest
from wol_roadmap_probe import decode_pagemap, live_blocks

class BlockPages(unittest.TestCase):
    def test_live_blocks_matches_frees_and_bounds(self):
        t='\n'.join([
            'WOL_ALLOC event=alloc ptr=0x1000 bytes=0x100 seq=0x1',
            'WOL_ALLOC event=alloc ptr=0x2000 bytes=0x800000 seq=0x2',
            'WOL_ALLOC event=alloc ptr=0x4000 bytes=0x4000000 seq=0x3',
            'WOL_ALLOC event=free ptr=0x4000 bytes=0x4000000 seq=0x4',
            'WOL_ALLOC event=realloc ptr=0x2000 bytes=0x900000 seq=0x5',
            'unrelated line'])
        self.assertEqual(live_blocks(t),[ (0x2000,0x900000) ])
        self.assertEqual(live_blocks(t,min_bytes=0x800001),[ (0x2000,0x900000) ])
        self.assertEqual(live_blocks(''),[])
    def test_pagemap_bits_present_swapped_file_exclusive(self):
        def entry(present=False,swapped=False,file_=False,exclusive=False):
            v=0
            v|=int(present)<<63;v|=int(swapped)<<62;v|=int(file_)<<61;v|=int(exclusive)<<60
            return v.to_bytes(8,'little')
        data=entry(present=True,exclusive=True)+entry(swapped=True)+entry(present=True,file_=True)+entry()
        self.assertEqual(decode_pagemap(data),dict(pages=4,present=2,swapped=1,file_or_shared=1,exclusive=1))
        with self.assertRaises(ValueError):decode_pagemap(b'x'*7)

if __name__=='__main__':unittest.main()

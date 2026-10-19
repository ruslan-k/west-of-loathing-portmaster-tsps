import struct
import unittest
from wol_sdk_heap_census import walk_spans

BASE=0x1000000000

class SDKHeapSpanCensus(unittest.TestCase):
    def fixture(self):
        image=bytearray(0x10000)
        struct.pack_into('<QQ',image,0,16,BASE+0x80)
        # 4 pages allocated, 8 pages free, 4 pages small-sizeclass allocated.
        for i,(offset,address,pages,kind,state) in enumerate(((0x200,BASE,4,0,1),
                                                            (0x240,BASE+0x4000,8,0,2),
                                                            (0x280,BASE+0xc000,4,3,1))):
            image[offset+0x12]=kind;image[offset+0x13]=state
            struct.pack_into('<QQ',image,offset+0x18,address,pages)
            index=(address-BASE)//4096
            for j in range(index,index+pages):struct.pack_into('<Q',image,0x80+j*8,BASE+offset)
        def read(address,size):
            if not BASE<=address<=BASE+len(image)-size:raise ValueError('out of bounds')
            return bytes(image[address-BASE:address-BASE+size])
        return image,read
    def test_exact_spans_cover_heap_without_byte_contents(self):
        _,read=self.fixture();doc=walk_spans(read,BASE,65536)
        self.assertEqual(doc['heap_pages'],16)
        self.assertEqual([(r['state'],r['sizeclass'],r['pages']) for r in doc['spans']],[(1,0,4),(2,0,8),(1,3,4)])
        self.assertFalse(doc['reclaim_safe'])
    def test_invalid_span_pointer_or_nonprogressing_extent_refused(self):
        image,read=self.fixture();struct.pack_into('<Q',image,0x80,0xdeadbeef)
        with self.assertRaises(ValueError):walk_spans(read,BASE,65536)
        image,read=self.fixture();struct.pack_into('<Q',image,0x220,0)
        with self.assertRaises(ValueError):walk_spans(read,BASE,65536)
    def test_page_table_bounds_and_state_guard(self):
        image,read=self.fixture();struct.pack_into('<Q',image,8,BASE+65536-1)
        with self.assertRaises(ValueError):walk_spans(read,BASE,65536)
        image,read=self.fixture();image[0x213]=9
        with self.assertRaises(ValueError):walk_spans(read,BASE,65536)

if __name__=='__main__':unittest.main()

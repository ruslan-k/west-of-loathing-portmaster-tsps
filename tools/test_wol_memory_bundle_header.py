import struct,unittest
from wol_bundle_header_probe import decode_header,readable_range

class BundleHeader(unittest.TestCase):
    def test_prefix_decoding_does_not_prove_liveness(self):
        x=decode_header(struct.pack('<4Q',0x1100,0,0,144392040),144392040)
        self.assertTrue(x['length_matches_read']);self.assertEqual(x['klass'],'0x1100')
        self.assertIn('not GC liveness',x['hypothesis'])
        self.assertFalse(decode_header(struct.pack('<4Q',0,0,0,0),144392040)['length_matches_read'])
        with self.assertRaises(ValueError):decode_header(b'bad',1)
    def test_only_bounded_single_readable_mapping(self):
        maps='1000-2000 rw-p 00000000 00:00 0\n2000-3000 ---p 00000000 00:00 0\n'
        self.assertTrue(readable_range(maps,0x1020,32))
        for address,size in ((0x1ff0,32),(0x2000,32),(0x1000,65),(-1,32),(2**64-1,32)):
            self.assertFalse(readable_range(maps,address,size))

if __name__=='__main__':unittest.main()

#!/usr/bin/env python3
"""Data-free acceptance tests for exact map pixel-space validation."""
from types import SimpleNamespace
import unittest
import verify_wol_map_pixel_space as verify


class PixelSpaceVerifierTests(unittest.TestCase):
    def original(self):
        return SimpleNamespace(m_Width=4,m_Height=4,m_TextureFormat=1,
            m_ImageCount=1,m_MipCount=3,image_data=bytes(range(21)),
            m_CompleteImageSize=21)

    def candidate(self, mips):
        data=self.original()
        n={1:16,2:20,3:21}[mips]
        data.m_MipCount=mips
        data.image_data=data.image_data[:n]
        data.m_CompleteImageSize=n
        return data

    def check(self, candidate, max_mip_levels=1):
        fn=getattr(verify,'validate_map_texture',None)
        self.assertTrue(callable(fn),'verifier lacks a tested explicit mip-tail contract')
        assert fn is not None
        fn(self.original(),candidate,max_mip_levels)

    def test_single_mip_preserves_original_dimensions_and_pixels(self):
        self.check(self.candidate(1))

    def test_two_mips_are_valid_when_explicitly_requested(self):
        self.check(self.candidate(2),2)

    def test_no_strip_accepts_original_chain(self):
        self.check(self.candidate(3),0)

    def test_halved_dimensions_are_rejected(self):
        data=self.candidate(1)
        data.m_Width=2
        with self.assertRaisesRegex(ValueError,'dimensions'):
            self.check(data)

    def test_altered_pixels_are_rejected(self):
        data=self.candidate(1)
        data.image_data=b'X'+data.image_data[1:]
        with self.assertRaisesRegex(ValueError,'byte-exact'):
            self.check(data)

    def test_unrequested_extra_mips_are_rejected(self):
        with self.assertRaisesRegex(ValueError,'mip'):
            self.check(self.candidate(2),1)

    def test_bad_image_size_is_rejected(self):
        data=self.candidate(1)
        data.m_CompleteImageSize=15
        with self.assertRaisesRegex(ValueError,'byte-exact'):
            self.check(data)


if __name__=='__main__':
    unittest.main()

#!/usr/bin/env python3
import importlib.util
from pathlib import Path
import unittest

class Wave2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        p=Path(__file__).with_name('wol_m4_stage_wave2.py')
        cls.m=None
        if p.exists():
            spec=importlib.util.spec_from_file_location('wave2',p)
            assert spec and spec.loader
            cls.m=importlib.util.module_from_spec(spec)
            spec.loader.exec_module(cls.m)

    def test_world_allowlist_does_not_admit_character_or_ui(self):
        self.assertIsNotNone(self.m, 'safe staged selector missing')
        assert self.m is not None
        eligible=self.m.eligible
        self.assertTrue(eligible('bg_canyon1','DXT5',512,512))
        for name in ('pc_face_sprites','horsebits','ui_background','map_bsbg','mainmapbg1','SpriteAtlasTexture-PC','font','random_prop'):
            self.assertFalse(eligible(name,'DXT5',512,512),name)
        self.assertFalse(eligible('bg_canyon1','DXT5',512,512,ui=True))
        self.assertFalse(eligible('bg_canyon1','ARGB4444',512,512))
        self.assertFalse(eligible('bg_canyon1','DXT5',512,128))

if __name__=='__main__':
    unittest.main()

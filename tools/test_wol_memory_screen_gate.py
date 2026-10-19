import unittest
from pathlib import Path
from wol_screen_gate import read_rgb, title_observation, gameplay_observation

ROOT=Path(__file__).resolve().parents[1]

class ScreenReadiness(unittest.TestCase):
    def test_real_title_and_splash_are_not_interchangeable(self):
        reference=ROOT/'evidence/uprender-scope/upscope-a1/title.png'
        known_splash=ROOT/'evidence/alloc-min/allocmin-b2/title.png'
        self.assertTrue(title_observation(reference)['is_title'])
        self.assertFalse(title_observation(known_splash)['is_title'])
        self.assertTrue(title_observation(ROOT/'evidence/alloc-min/allocmin-b2/map.png')['is_title'])
        self.assertFalse(title_observation(ROOT/'evidence/uprender-scope/upscope-b1/map.png')['is_title'])
        self.assertFalse(title_observation(ROOT/'evidence/uprender-scope/upscope-b1/world.png')['is_title'])
    def test_hud_rejects_splash_and_menu(self):
        self.assertTrue(gameplay_observation(ROOT/'evidence/uprender-scope/upscope-b1/world.png')['has_game_hud'])
        for relative in ('evidence/uprender-scope/upscope-a1/title.png',
                         'evidence/alloc-min/allocmin-b2/title.png',
                         'evidence/alloc-min/allocmin-b2/restored-menu.png'):
            self.assertFalse(gameplay_observation(ROOT/relative)['has_game_hud'],relative)
    def test_transient_missing_framebuffer_uses_title_deadline(self):
        from wol_screen_gate import wait_for_title
        clock=[0.0];calls=[];records=[]
        def capture():
            calls.append(1)
            if len(calls)<=2:raise RuntimeError('no framebuffer after six captures')
        def pause(seconds):clock[0]+=seconds
        result=wait_for_title(capture,ROOT/'evidence/uprender-scope/upscope-a1/title.png',
                              lambda:True,records.append,seconds=30,period=5,
                              now=lambda:clock[0],pause=pause)
        self.assertTrue(result['is_title'])
        self.assertEqual(len(calls),3)
        self.assertFalse(records[0]['is_title'])
        self.assertIn('no framebuffer',records[0]['capture_error'])
        with self.assertRaisesRegex(RuntimeError,'runtime identity'):
            wait_for_title(capture,ROOT/'evidence/uprender-scope/upscope-a1/title.png',lambda:False,records.append)
    def test_reference_rgb_shape(self):
        w,h,data=read_rgb(ROOT/'evidence/uprender-scope/upscope-a1/title.png')
        self.assertEqual((w,h,len(data)),(1280,720,2764800))

if __name__=='__main__':unittest.main()

import unittest
from wol_present_watchdog import PresentationStall, require_progress

class PresentWatchdog(unittest.TestCase):
    def test_recent_present_does_not_require_animated_pixels(self):
        x=require_progress('MOMO_FRAME frame=7 ns=9000000000\n',10000000000,5)
        self.assertEqual(x,{'frame':7,'ns':9000000000,'age_s':1})
    def test_audio_hid_and_liveness_are_not_present_progress(self):
        with self.assertRaises(PresentationStall) as c:
            require_progress('MOMO_FRAME frame=1481 ns=1000000000\nHID_SAMPLE number=99\nAUDOUT_HOST_PROFILE consumed-frames=999\n',7000000000,5)
        self.assertEqual(c.exception.observation['frame'],1481)
        self.assertEqual(c.exception.observation['age_s'],6)
        with self.assertRaises(PresentationStall):require_progress('audio only',7000000000,5)
    def test_future_clock_and_bad_budget_refuse(self):
        with self.assertRaises(ValueError):require_progress('MOMO_FRAME frame=1 ns=9000000000',1000000000,5)
        with self.assertRaises(ValueError):require_progress('',0,0)

if __name__=='__main__':unittest.main()

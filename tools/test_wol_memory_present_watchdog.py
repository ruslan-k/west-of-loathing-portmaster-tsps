import unittest
from wol_present_watchdog import PresentationStall, require_progress, phase_budget, run_monitored
from unittest.mock import Mock
import subprocess

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
    def test_settled_five_seconds_and_transition_thirty_are_distinct(self):
        self.assertEqual(phase_budget(True,5,30),5)
        self.assertEqual(phase_budget(False,5,30),30)
        self.assertEqual(phase_budget(True,0,30),30)  # backward-compatible opt-in
        text='MOMO_FRAME frame=55 ns=1000000000'
        self.assertEqual(require_progress(text,12_000_000_000,phase_budget(False,5,30))['age_s'],11)
        with self.assertRaises(PresentationStall):
            require_progress(text,12_000_000_000,phase_budget(True,5,30))
    def test_bad_adaptive_budgets_fail_closed(self):
        for stable,transition in ((5,float('nan')),(float('nan'),30),(10,5),(4,30),(5,31)):
            with self.assertRaises(ValueError):phase_budget(True,stable,transition)
        with self.assertRaises(ValueError):phase_budget('false',5,30)
    def test_monitor_checks_while_input_helper_waits(self):
        child=Mock();child.wait.side_effect=[subprocess.TimeoutExpired('fixture',1),0]
        child.poll.return_value=0;check=Mock();factory=Mock(return_value=child)
        run_monitored(['fixture'],check,popen=factory)
        self.assertEqual(check.call_count,2)
        child.terminate.assert_not_called()
    def test_stall_terminates_only_owned_helper_and_preserves_error(self):
        child=Mock();child.wait.side_effect=[subprocess.TimeoutExpired('fixture',1),0]
        child.poll.return_value=None;failure=PresentationStall({'frame':55})
        with self.assertRaises(PresentationStall) as c:
            run_monitored(['fixture'],Mock(side_effect=failure),popen=Mock(return_value=child))
        self.assertIs(c.exception,failure)
        child.terminate.assert_called_once_with()
        self.assertEqual(child.wait.call_args.kwargs['timeout'],3)
    def test_input_helper_failure_is_not_a_successful_trial(self):
        child=Mock();child.wait.return_value=7;child.poll.return_value=7
        with self.assertRaises(subprocess.CalledProcessError):
            run_monitored(['fixture'],Mock(),popen=Mock(return_value=child))
    def test_future_clock_and_bad_budget_refuse(self):
        with self.assertRaises(ValueError):require_progress('MOMO_FRAME frame=1 ns=9000000000',1000000000,5)
        with self.assertRaises(ValueError):require_progress('',0,0)

if __name__=='__main__':unittest.main()

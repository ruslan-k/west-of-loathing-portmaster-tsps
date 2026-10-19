import json
from pathlib import Path
import subprocess
import sys
import unittest
from wol_acceptance_batch import COMMON, ORDER, plan_trial

ROOT=Path(__file__).resolve().parent.parent


class AcceptanceProtocol(unittest.TestCase):
    def test_resume_plan_skips_collects_or_runs(self):
        self.assertEqual(plan_trial(True,True,True),'skip')
        self.assertEqual(plan_trial(False,True,False),'fail-partial')
        self.assertEqual(plan_trial(False,False,True),'collect')
        self.assertEqual(plan_trial(False,False,False),'run')
    def test_three_alternating_pairs_and_only_size_treatment(self):
        self.assertEqual(tuple(x.split('-')[1][0] for x in ORDER),('a','b','b','a','a','b'))
        self.assertEqual(len(set(ORDER)),6)
        a=dict(COMMON,WOL_UPRENDER_720='0');b=dict(COMMON,WOL_UPRENDER_720='1')
        self.assertEqual([k for k in a if a[k]!=b[k]],['WOL_UPRENDER_720'])
        for key in ('WOL_ALLOC_TRACE','WOL_UPRENDER_TRACE','WOL_RT_ORIGIN','WOL_GPU_RESIDENCY','T2_TRANSFER_SPARSE_COPY'):
            self.assertEqual(a[key],'0')
    def test_route_is_bounded_and_does_not_inject_exit_chord(self):
        route=json.loads((ROOT/'evidence/accept-720/route-gulch.json').read_text())
        self.assertEqual(len(route),24)
        self.assertEqual(len({x['label'] for x in route}),24)
        for action in route:
            self.assertTrue(1<=action['hold_ms']<=2000)
            self.assertTrue(1<=action['wait_s']<=30)
            self.assertNotEqual(int(action['buttons'],0)&0xc00,0xc00)
            self.assertIsInstance(action.get('settled',False),bool)
    def test_host_runner_refuses_bad_identifiers_before_ssh(self):
        for label,sha,env in (('../bad','0'*64,'{}'),('safe','A'*64,'{}'),('safe','0'*64,'{"WOL_X":1}')):
            r=subprocess.run([sys.executable,str(ROOT/'tools/wol_owned_probe.py'),label,
                '--elf',sha,'--layout','unused','--out','unused','--env',env],capture_output=True,text=True)
            self.assertEqual(r.returncode,2,r.stdout+r.stderr)
            self.assertIn('error:',r.stderr)


if __name__=='__main__':unittest.main()

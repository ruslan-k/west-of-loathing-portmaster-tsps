import unittest
from wol_uprender_report import compare_runs, performance_summary

class UpRenderComparison(unittest.TestCase):
    def row(self,label,variant,**extra) -> dict:
        return dict(label=label,runtime_sha256='same',section_sha256='section',control_save_hashes={'save':'sha'},
                    effective_env=dict(WOL_UPRENDER_720=variant,COTM_RUN_ID=label,WOL_GUEST_RT720='0',**extra))
    def test_only_treatment_and_run_id_can_differ(self):
        a=self.row('a','0');b=self.row('b','1')
        r=compare_runs([a,b]);self.assertEqual(r['arm_counts'],{'control':1,'uprender720':1})
        self.assertTrue(r['matched_identity']);self.assertTrue(r['matched_other_env'])
        b['effective_env']['UNRELATED']='1';self.assertFalse(compare_runs([a,b])['matched_other_env'])
        b['runtime_sha256']='other';self.assertFalse(compare_runs([a,b])['matched_identity'])
    def test_explicit_treatment_required(self):
        r=self.row('a','0');del r['effective_env']['WOL_UPRENDER_720']
        with self.assertRaises(ValueError):compare_runs([r])

    def test_absent_frame_window_excluded_not_zero_or_success(self):
        a=self.row('a','0');b=self.row('b','1');failed=self.row('frozen','0')
        for r,fps,p95 in ((a,24,45),(b,33,32)):
            r['phases']={'game-idle':{'frame_window':{'available':True,'seconds':28,'presents_per_s':fps,'p95_ms':p95}}}
        failed['phases']={'game-idle':{'frame_window':{'available':False,'frames':0}}}
        x=performance_summary([a,failed,b]);self.assertEqual(x['valid_arm_counts'],{'control':1,'uprender720':1})
        self.assertEqual(x['excluded'][0]['label'],'frozen')
        self.assertEqual(x['arms']['control']['presents_per_s']['median'],24)
        self.assertEqual(x['arms']['uprender720']['p95_ms']['median'],32)
        self.assertIsNone(x['runs'][0]['mali_commit_mib'])

if __name__=='__main__':unittest.main()

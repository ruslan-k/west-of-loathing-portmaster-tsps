import unittest
from wol_uprender_report import compare_runs

class UpRenderComparison(unittest.TestCase):
    def row(self,label,variant,**extra):
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

if __name__=='__main__':unittest.main()

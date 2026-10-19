import unittest
from wol_sparse_report import PHASES, sparse_vma


class SparseReportFunctions(unittest.TestCase):
    def test_sparse_vma_picks_the_cold_anon_transfer_backing(self):
        rows=[{'path':'[anon rw]','size_mib':72.0,'swap_mib':64.1},
              {'path':'[anon rw]','size_mib':1524.7,'swap_mib':295.2},
              {'path':'/dev/shm/x','size_mib':72.0,'swap_mib':64.1},
              {'path':'[anon rw]','size_mib':96.0,'swap_mib':0.0}]
        pick=sparse_vma(rows)
        self.assertIsNotNone(pick)
        assert pick is not None
        self.assertEqual(pick['size_mib'],72.0)
    def test_no_transfer_vma_is_none(self):
        self.assertIsNone(sparse_vma([{'path':'[anon rw]','size_mib':1524.7,'swap_mib':295.2}]))
    def test_phase_sequence_is_fixed(self):
        self.assertEqual(PHASES,('startup','menu','game-idle','precleanup'))


if __name__=='__main__':unittest.main()

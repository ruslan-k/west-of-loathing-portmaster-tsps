import unittest
from wol_allocmin_report import arena_join, bands, totals


class AllocMinReport(unittest.TestCase):
    def test_bands_and_totals_split_by_requested_size(self):
        blocks=[
            dict(ptr='0x1000',requested_kib=300,present_kib=200,swapped_kib=100,caller='a+0x1'),   # 256K..512K
            dict(ptr='0x2000',requested_kib=700,present_kib=500,swapped_kib=100,caller='a+0x1'),   # 512K..1M
            dict(ptr='0x3000',requested_kib=2048,present_kib=1000,swapped_kib=500,caller='b+0x2'), # 1M..4M
            dict(ptr='0x4000',requested_kib=131072,present_kib=10000,swapped_kib=8000,caller='b+0x2'),
            dict(ptr='0x5000',requested_kib=64,error='short read',caller='c+0x3')]
        rows=bands(blocks)
        self.assertEqual(rows[0],dict(lo_bytes=1<<18,hi_bytes=1<<19,blocks=1,requested_mib=0.3,present_mib=0.2,swapped_mib=0.1))
        self.assertEqual(rows[1]['blocks'],1)
        self.assertEqual(rows[2]['blocks'],1)
        self.assertEqual(rows[5]['blocks'],1)
        self.assertEqual(rows[5]['swapped_mib'],7.8)
        self.assertEqual(totals(blocks),dict(blocks=4,errors=1,requested_mib=131.0,present_mib=11.4,swapped_mib=8.5))
    def test_arena_join_splits_tracked_from_unattributed(self):
        vmas=[dict(start='0x100000000',end='0x150000000',size_mib=1280,swap_mib=1000.0),
             dict(start='0x170000000',end='0x170400000',size_mib=4,swap_mib=1.0)]
        blocks=[dict(ptr='0x110000000',requested_kib=512,present_kib=300,swapped_kib=200),
                dict(ptr='0x200000000',requested_kib=512,present_kib=300,swapped_kib=200)]
        rows=arena_join(vmas,blocks)
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]['tracked_inside'],1)
        self.assertEqual(rows[0]['tracked_inside_swapped_mib'],0.2)
        self.assertEqual(rows[0]['unattributed_swap_mib'],999.8)


if __name__=='__main__':
    unittest.main()

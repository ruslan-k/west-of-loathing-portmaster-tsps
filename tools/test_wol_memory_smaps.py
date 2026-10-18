import unittest
from wol_roadmap_probe import parse_smaps

SAMPLE='''55d0a8c000-55d0b1a000 r-xp 00000000 08:02 123 /usr/bin/wol-horizon
Size:                568 kB
Rss:                 384 kB
Pss:                 380 kB
Pss_Anon:            0 kB
SwapPss:              12 kB
7f0000000000-7f0001000000 rw-p 00000000 00:00 0
Size:              16384 kB
Rss:               10240 kB
Pss:               10100 kB
SwapPss:            9040 kB
7ffce4c20000-7ffce4c60000 rw-p 00000000 00:00 0 [stack]
Rss:                  12 kB
Pss:                  12 kB
SwapPss:               0 kB
'''

class SmapsParse(unittest.TestCase):
    def test_rows_paths_and_fields(self):
        rows=parse_smaps(SAMPLE)
        self.assertEqual(len(rows),3)
        self.assertEqual(rows[0]['path'],'/usr/bin/wol-horizon')
        self.assertEqual(rows[0]['perms'],'r-xp')
        self.assertEqual(rows[0]['size_kib'],0x8e000//1024 if False else (0x55d0b1a000-0x55d0a8c000)//1024)
        self.assertEqual(rows[0]['pss_kib'],380)
        self.assertEqual(rows[1]['path'],'')
        self.assertEqual(rows[1]['swap_kib'],9040)
        self.assertEqual(rows[2]['path'],'[stack]')
    def test_empty_input(self):
        self.assertEqual(parse_smaps(''),[])

if __name__=='__main__':unittest.main()

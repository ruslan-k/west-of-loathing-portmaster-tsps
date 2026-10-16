#!/usr/bin/env python3
"""Data-free tests for roadmap report contracts and recovered-menu signal gating."""
import struct
import os
import subprocess
import tempfile
import unittest
import zlib
from pathlib import Path
from wol_roadmap_analyze import allocation_ledger, compare, distribution
from wol_roadmap_probe import kms_rgb_signal


def png_rgb8(pixels, color=2):
    def chunk(kind, body):
        return struct.pack('>I',len(body))+kind+body+struct.pack('>I',zlib.crc32(kind+body))
    return (b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',2,1,8,color,0,0,0))
            +chunk(b'IDAT',zlib.compress(b'\0'+pixels))+chunk(b'IEND',b''))


class ReportContracts(unittest.TestCase):
    def test_launcher_injection_default_off_preserves_explicit_opt_in(self):
        launcher=Path(__file__).resolve().parents[1]/'West of Loathing Switch.sh'
        lines=[s for s in launcher.read_text().splitlines() if s.startswith('export COTM_INPUT_DIAGNOSTIC=')]
        self.assertEqual(len(lines),1)
        for option,expected in ((None,'0'),('0','0'),('1','1')):
            env=dict(os.environ);env.pop('COTM_INPUT_DIAGNOSTIC',None)
            if option is not None:env['COTM_INPUT_DIAGNOSTIC']=option
            r=subprocess.run(['/bin/bash','-c',lines[0]+'; printf %s "$COTM_INPUT_DIAGNOSTIC"'],env=env,capture_output=True,text=True,check=True)
            self.assertEqual(r.stdout,expected)

    def test_read_span_joins_containing_allocation_not_just_equal_base(self):
        text='''WOL_ALLOC event=alloc ptr=0x1000 bytes=0x100 arena=0x1 incomplete=0 parent=a parent=b
WOL_ROMFS_BUFFER address=0x1020 bytes=100
NVN_MEMORY_POOL_BOUND address=0x1040 size=0x40
WOL_ROMFS_BUFFER address=0x10f0 bytes=32
WOL_ALLOC event=free ptr=0x1000 bytes=0x100 incomplete=0
'''
        d=allocation_ledger(text)
        self.assertEqual(d['romfs_reads'][0]['containing_at_event'][0]['ptr'],'0x1000')
        self.assertEqual(d['romfs_reads'][0]['containing_at_event'][0]['parents'],['a','b'])
        self.assertEqual(d['romfs_reads'][1]['containing_at_event'],[])
        self.assertEqual(d['SDK_requested_live_bytes'],0)
        self.assertFalse(d['trace_incomplete'])
        self.assertIsNone(d['safe_reclaimable_bytes'])

    def test_pool_views_are_not_added_as_new_heap(self):
        d=allocation_ledger('''WOL_ALLOC event=alloc ptr=0x1000 bytes=0x100 incomplete=0
NVN_MEMORY_POOL_BOUND address=0x1020 size=0x40
NVN_MEMORY_POOL_BOUND address=0x1040 size=0x40
WOL_ALLOC event=alloc ptr=0x2000 bytes=0x20 incomplete=0
''')
        self.assertEqual(d['SDK_requested_live_bytes'],288)
        self.assertEqual(d['SDK_requested_ever_pool_bound_live_bytes'],256)
        self.assertEqual(d['SDK_requested_no_observed_pool_binding_live_bytes'],32)

    def test_reused_address_is_not_old_pool_owner(self):
        d=allocation_ledger('''WOL_ALLOC event=alloc ptr=0x1000 bytes=0x100 incomplete=0
NVN_MEMORY_POOL_BOUND address=0x1020 size=0x40
WOL_ALLOC event=free ptr=0x1000 bytes=0x100 incomplete=0
WOL_ALLOC event=alloc ptr=0x1000 bytes=0x100 incomplete=0
''')
        self.assertEqual(d['SDK_requested_ever_pool_bound_live_bytes'],0)
        self.assertEqual(d['SDK_requested_no_observed_pool_binding_live_bytes'],256)

    def test_unknown_counter_is_not_zero(self):
        self.assertEqual(distribution([None]),{'available':False})
        self.assertEqual(distribution([0])['median'],0)

    def test_nonmatched_saves_refuse_comparison(self):
        def run(on,save):
            return dict(effective_env={'WOL_ASTC_POSTCOPY':str(on)},runtime_sha256='same',section_sha256='same',control_save_hashes={'x':save},phases={})
        self.assertFalse(compare([run(0,'a'),run(1,'b')])['matched_identity'])

    def test_kms_capture_success_does_not_validate_all_black_menu(self):
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'frame.png'
            p.write_bytes(png_rgb8(bytes(6)))
            self.assertFalse(kms_rgb_signal(p))
            p.write_bytes(png_rgb8(b'\0\0\0\x40\x40\x40'))
            self.assertTrue(kms_rgb_signal(p))
            p.write_bytes(png_rgb8(bytes(6),color=6))
            self.assertFalse(kms_rgb_signal(p))
            p.write_bytes(b'not png')
            self.assertFalse(kms_rgb_signal(p))


if __name__=='__main__':
    unittest.main()

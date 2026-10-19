#!/usr/bin/env python3
"""Contract test for the frozen TransferMemory sparse-copy block (roadmap §16.5).

The scan loop is copied verbatim from the frozen build source native/memory.h
(upstream sha256 68974762e5551fbc57f6753e1c9c311488bcf2283642806e35051778be96ed8b).
This test verifies the embedded span hash and runs the compiled matrix.
"""
import hashlib
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parent.parent
FIXTURE=ROOT/'tools/fixtures/t2_sparse_copy_fixture.c'
VERBATIM_SHA='4f146003c1c920928f540a8dd067052a4f44ce69c2134b403b50ad34086c3041'
TAIL='} else memcpy(copy,(void *)(uintptr_t)address,size);'


def verbatim_span(text):
    start=text.index('uint64_t copied=size,skipped=0;')
    end=text.index(TAIL)+len(TAIL)
    return text[start:end]


class SparseCopyContract(unittest.TestCase):
    def test_fixture_span_is_the_frozen_build_block(self):
        self.assertEqual(hashlib.sha256(verbatim_span(FIXTURE.read_text()).encode()).hexdigest(),VERBATIM_SHA)
    def test_contract_matrix_compiles_and_passes(self):
        cc=shutil.which('cc') or shutil.which('gcc')
        if not cc:self.skipTest('no host C compiler')
        with tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR') or None) as folder:
            exe=Path(folder)/'fixture'
            subprocess.run([cc,'-O1','-o',str(exe),str(FIXTURE)],check=True)
            run=subprocess.run([str(exe),'small'],capture_output=True,text=True)
        self.assertEqual(run.returncode,0,run.stdout+run.stderr)
        cases={line.split()[1]:dict(p.split('=') for p in line.split()[2:])
               for line in run.stdout.splitlines() if line.startswith('CASE ')}
        self.assertEqual(set(cases),{'all_zero','sparse_mixed','read_after_write','dense','double_creation','copyback'})
        for name,row in cases.items():
            self.assertEqual(row['ok'],'1',(name,run.stdout))
        self.assertIn('RESULT failures=0',run.stdout)


if __name__=='__main__':unittest.main()

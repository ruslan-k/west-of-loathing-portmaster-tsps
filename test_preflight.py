import copy
import json
import os
import pathlib
import tempfile
import unittest
from inspect_nso import inspect_nso, inspect_bundle
from map_preflight import preflight

ROOT = pathlib.Path(__file__).resolve().parent

class PreflightTests(unittest.TestCase):
    def test_nso_rejects_wrong_magic(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR')) as folder:
            path = pathlib.Path(folder)/'invalid'
            path.write_bytes(b'NOT0'+bytes(252))
            with self.assertRaisesRegex(ValueError,'not NSO0'):
                inspect_nso(path)

    @unittest.skipUnless((ROOT/'wol-base/exefs/rtld').exists(),'owner integration input absent')
    def test_real_nso_detects_modified_segment(self):
        original = bytearray((ROOT/'wol-base/exefs/rtld').read_bytes())
        original[-1] ^= 1
        with tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR')) as folder:
            path = pathlib.Path(folder)/'rtld'
            path.write_bytes(original)
            with self.assertRaises((ValueError,RuntimeError)):
                inspect_nso(path)

    def test_bundle_rejects_truncation(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR')) as folder:
            path = pathlib.Path(folder)/'bad-bundle'
            path.write_bytes(b'UnityFS')
            with self.assertRaisesRegex(ValueError,'truncated'):
                inspect_bundle(path)

    @unittest.skipUnless((ROOT/'wol-analysis.json').exists(),'owner integration input absent')
    def test_map_rejects_unimplemented_relocation(self):
        report = json.loads((ROOT/'wol-analysis.json').read_text())
        report['modules'][0]['relocations'][0]['type'] = 99999
        with self.assertRaisesRegex(ValueError,'unsupported relocation'):
            preflight(ROOT/'wol-base',report)

    @unittest.skipUnless((ROOT/'wol-analysis.json').exists(),'owner integration input absent')
    def test_map_rejects_segment_identity_mismatch(self):
        report = json.loads((ROOT/'wol-analysis.json').read_text())
        report['modules'][0]['segments'][0]['sha256'] = '0'*64
        with self.assertRaisesRegex(ValueError,'segment identity mismatch'):
            preflight(ROOT/'wol-base',report)

if __name__ == '__main__':
    unittest.main()

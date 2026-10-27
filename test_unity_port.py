#!/usr/bin/env python3
"""Canonical package/launcher contract, without proprietary owner data."""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import unittest

ROOT = Path(__file__).resolve().parent
PORT = ROOT / 'port'
GAME = PORT / 'westofloathing'

class PromotedPort(unittest.TestCase):
    def test_canonical_launcher_parity(self):
        launcher = PORT / 'West of Loathing.sh'
        self.assertEqual(launcher.read_bytes(), (ROOT / 'West of Loathing.sh').read_bytes())
        source = launcher.read_text()
        self.assertIn('GAMEDIR="/mnt/SDCARD/Roms/PORTS/westofloathing"', source)
        self.assertNotIn('wol-switch', source)
        self.assertNotIn('wol-unity', source)
        subprocess.run(['/bin/sh', '-n', str(launcher)], check=True)

    def test_only_current_port_is_shipped(self):
        self.assertEqual(sorted(p.name for p in PORT.iterdir()), ['README.md', 'West of Loathing.sh', 'westofloathing'])
        self.assertTrue((GAME / 'ua_host').is_file())
        self.assertFalse(any(p.suffix in ('.apk', '.obb', '.seg') for p in PORT.rglob('*')))
        self.assertFalse((GAME / 'lib/libunity.so').exists())
        self.assertFalse((GAME / 'lib/libmain.so').exists())
        self.assertFalse((GAME / 'data').exists())

    def test_zero_budget_selects_normal_launch(self):
        source = (PORT / 'West of Loathing.sh').read_text()
        line = next(l for l in source.splitlines() if l.startswith('if [ -n "${WOL_PROBE_SECONDS'))
        for value, expected in [('', 'normal'), ('0', 'normal'), ('10', 'bounded')]:
            result = subprocess.check_output(['/bin/sh', '-c', line + '\n echo bounded; else echo normal; fi'],
                                             env=dict(os.environ, WOL_PROBE_SECONDS=value), text=True)
            self.assertEqual(result.strip(), expected)

    def test_owner_package_inputs_are_ignored(self):
        for rel in ['port/westofloathing/assets/owner.dll', 'port/westofloathing/android_package.json',
                    'port/westofloathing/plugins.map', 'port/westofloathing/.run.lock']:
            result = subprocess.run(['git', 'check-ignore', '-q', '--no-index', rel], cwd=ROOT)
            self.assertEqual(result.returncode, 0, rel)

    def test_generic_bridge_is_not_a_game_il2cpp_library(self):
        self.assertEqual(hashlib.sha256((GAME / 'lib/libil2cpp.so').read_bytes()).hexdigest(),
                         'a8e31d63f61d9852afa47e5f6642db880f101c7327816708dcfe7a85d747ac3d')

    def test_redistributable_runtime_manifest(self):
        manifest = json.loads((GAME / 'runtime-manifest.json').read_text())
        expected = set(manifest['files'])
        actual = {p.relative_to(GAME).as_posix() for p in GAME.rglob('*')
                  if p.is_file() and p.name != 'runtime-manifest.json' and '__pycache__' not in p.parts}
        self.assertEqual(actual, expected)
        expected_dirs = {Path(name).parent.as_posix() for name in expected if '/' in name}
        actual_dirs = {p.relative_to(GAME).as_posix() for p in GAME.rglob('*')
                       if p.is_dir() and p.name != '__pycache__'}
        self.assertEqual(actual_dirs, expected_dirs)
        self.assertFalse(any(p.is_symlink() for p in GAME.rglob('*')))
        for rel, expected in manifest['files'].items():
            with self.subTest(path=rel):
                p = GAME / rel
                self.assertEqual(p.stat().st_size, expected['bytes'])
                self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(), expected['sha256'])
        self.assertEqual(manifest['files']['ua_host']['sha256'],
                         '2408581859254d93d7a0f2eca9828a63dfe21af63593f7013c3d3aeb20a21b50')

if __name__ == '__main__':
    unittest.main()

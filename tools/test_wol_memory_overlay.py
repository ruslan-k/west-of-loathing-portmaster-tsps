#!/usr/bin/env python3
"""Synthetic GPL-overlay interface fixtures, no extracted game content."""
import tempfile
import unittest
from pathlib import Path
from wol_overlay_verify import verify


class OverlayTests(unittest.TestCase):
    def test_apply_and_byte_exact_parity_rejects_stale_source(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            for name, data in [('base', 'old\n'), ('ref', 'new\n')]:
                (root/name/'native').mkdir(parents=True)
                (root/name/'native/test.h').write_text(data)
            overlay = root/'overlay.patch'
            overlay.write_text('--- a/native/test.h\n+++ b/native/test.h\n@@ -1 +1 @@\n-old\n+new\n')
            result = verify(root/'base', root/'ref', overlay)
            self.assertEqual(len(result['native_files']), 1)
            (root/'ref/native/test.h').write_text('stale\n')
            with self.assertRaises(ValueError):
                verify(root/'base', root/'ref', overlay)


if __name__ == '__main__':
    unittest.main()

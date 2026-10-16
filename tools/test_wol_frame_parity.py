#!/usr/bin/env python3
"""Data-free tests for the KMS frame-parity tool (synthetic PNG fixtures)."""
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from wol_png_lite import write_png, read_png
from wol_frame_parity import metrics, stable_mask, VISIBLE

W, H = 8, 4


def flat(r=10, g=20, b=30):
    return bytes((r, g, b)) * (W*H)


def with_blob(rgb, x, y, w, h, value=(250, 250, 250)):
    buf = bytearray(rgb)
    for yy in range(y, y+h):
        for xx in range(x, x+w):
            i = (yy*W+xx)*3
            buf[i:i+3] = bytes(value)
    return bytes(buf)


class ParityTests(unittest.TestCase):
    def test_identical_frames_report_no_difference(self):
        frame = (W, H, flat())
        m = metrics(frame, frame)
        self.assertEqual(m['differing_pixels'], 0)
        self.assertEqual(m['mean_max_channel_delta'], 0)
        self.assertEqual(m['hot_clusters'], [])

    def test_one_level_dither_is_counted_but_not_visible(self):
        m = metrics((W, H, flat()), (W, H, flat(11, 20, 30)))
        self.assertGreater(m['differing_pixels'], 0)
        self.assertEqual(m['pixels_over_threshold'], 0)
        self.assertEqual(m['worst_max_channel_delta'], 1)

    def test_visible_blob_is_localised_to_its_own_bbox(self):
        a = (W, H, flat())
        b = (W, H, with_blob(flat(), 2, 1, 3, 2))
        m = metrics(a, b)
        self.assertEqual(m['pixels_over_threshold'], 6)
        clusters = m['hot_clusters']
        assert isinstance(clusters, list)
        self.assertEqual(len(clusters), 1)
        self.assertEqual(clusters[0]['pixels'], 6)
        self.assertEqual((clusters[0]['x'], clusters[0]['y'], clusters[0]['w'], clusters[0]['h']), (2, 1, 3, 2))
        self.assertTrue(m['worst_max_channel_delta'] > VISIBLE)

    def test_stable_mask_excludes_pixels_that_vary_between_repeats(self):
        f1 = (W, H, flat())
        f2 = (W, H, with_blob(flat(), 0, 0, 1, 1))       # animation pixel
        f3 = (W, H, with_blob(flat(), 0, 0, 1, 1, (99, 99, 99)))
        mask, first, w, h = stable_mask([f1, f2, f3])
        self.assertEqual((w, h), (W, H))
        self.assertEqual(mask[0], 0)
        self.assertEqual(sum(mask), W*H - 1)
        self.assertEqual(first, f1[2])

    def test_cli_writes_report_and_flags_between_arm_change(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            for name, blob in (('v2-run-control-1', False), ('v2-run-control-2', False),
                               ('v2-run-postcopy-1', True)):
                arm = root/name
                arm.mkdir()
                rgb = with_blob(flat(), 1, 1, 2, 2) if blob else flat()
                write_png(arm/'map.png', W, H, rgb)
            out = root/'report.json'
            frames = sorted(str(p) for p in root.glob('*/map.png'))
            subprocess.run([sys.executable, str(Path(__file__).resolve().parent/'wol_frame_parity.py'),
                            *frames, '--scene', 'fixture', '--size', '%dx%d' % (W, H), '--stable-arm', 'control',
                            '--out', str(out)], check=True, capture_output=True, text=True)
            report = __import__('json').loads(out.read_text())
            self.assertEqual(report['scene'], 'fixture')
            self.assertEqual(report['verdict'].split(':')[0], 'review')  # a visible blob is a real between-arm difference
            stable = report['stable_mask']
            self.assertEqual(stable['arm'], 'control')
            self.assertEqual(len(stable['violations']), 1)
            self.assertEqual(stable['violations'][0]['stable_pixels_violated'], 4)
            self.assertEqual(stable['verdict'], 'stable_content_differs')
            self.assertEqual(len(read_png(root/'v2-run-postcopy-1'/'map.png')[2]), W*H*3)


if __name__ == '__main__':
    unittest.main()

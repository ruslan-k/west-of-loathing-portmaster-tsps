#!/usr/bin/env python3
"""Host test: compile the LD_PRELOAD shim + driver and prove the log contract."""
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SHIM = REPO / "tools" / "wol_hostmmap_shim.c"
DRIVER = REPO / "tools" / "wol_hostmmap_selftest.c"


def host_cc():
    for name in ("cc", "gcc", "/usr/sbin/gcc"):
        path = shutil.which(name) or (name if Path(name).exists() else None)
        if path:
            return path
    raise unittest.SkipTest("no host C compiler")


class HostMmapShimTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cc = host_cc()
        cls.tmp = Path(tempfile.mkdtemp(prefix="wol-hostmmap-"))
        shim_so = cls.tmp / "libwol_hostmmap_selftest.so"
        driver = cls.tmp / "selftest"
        subprocess.run([cls.cc, "-O1", "-g", "-fno-omit-frame-pointer", "-fPIC", "-shared",
                        str(SHIM), "-o", str(shim_so), "-ldl", "-pthread"], check=True)
        subprocess.run([cls.cc, "-O1", "-g", "-fno-omit-frame-pointer",
                        str(DRIVER), "-o", str(driver)], check=True)
        cls.log = cls.tmp / "hostmmap.log"
        env = dict(os.environ, LD_PRELOAD=str(shim_so), WOL_HOSTMMAP_LOG=str(cls.log),
                   WOL_HOSTMMAP_MIN=str(1 << 20))
        result = subprocess.run([str(driver)], env=env, capture_output=True, text=True)
        cls.driver_rc = result.returncode
        cls.driver_out = result.stdout + result.stderr
        cls.lines = cls.log.read_text().splitlines() if cls.log.exists() else []

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp, ignore_errors=True)

    def test_driver_ran(self):
        self.assertEqual(self.driver_rc, 0, self.driver_out)
        self.assertIn("SELFTEST_OK", self.driver_out)

    def test_each_big_operation_logged_once(self):
        self.assertEqual(self.driver_rc, 0, self.driver_out)
        for op, size in (("mmap", 6 * 1024 * 1024), ("malloc", 5 * 1024 * 1024),
                         ("calloc", 7 * 1024 * 1024), ("munmap", 6 * 1024 * 1024)):
            hits = [l for l in self.lines if f"op={op} " in l and f"size={size} " in l]
            self.assertEqual(len(hits), 1, f"{op} {size}: {self.lines}")

    def test_small_allocation_not_logged(self):
        self.assertFalse([l for l in self.lines if "size=1024 " in l], self.lines)

    def test_line_shape(self):
        for line in self.lines:
            self.assertRegex(line, r"^HOSTMMAP ts=\d+ op=\w+ pid=\d+ size=\d+ .*ret=\S+ frames=.*;$|^HOSTMMAP ts=\d+ op=\w+ pid=\d+ size=\d+ ret=\S+ frames=.*;$")

    def test_frames_name_the_driver(self):
        hits = [l for l in self.lines if "op=malloc " in l]
        self.assertTrue(any("selftest+0x" in l for l in hits), hits)

    def test_mmap_flags_present(self):
        hits = [l for l in self.lines if "op=mmap " in l]
        self.assertTrue(hits and re.search(r"prot=0x3 flags=0x22", hits[0]), hits)


if __name__ == "__main__":
    unittest.main()

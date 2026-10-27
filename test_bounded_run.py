import contextlib
import io
import os
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

import importlib.util

_spec = importlib.util.spec_from_file_location('bounded_run', Path(__file__).resolve().parent / 'port/westofloathing/bounded_run.py')
assert _spec is not None and _spec.loader is not None
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)
run = _module.run


class BoundTest(unittest.TestCase):
    def test_deadline_reaps_only_own_child(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / 'logs').mkdir()
            source = root / 'sleeper.c'
            source.write_text('#include <unistd.h>\nint main(void) { sleep(30); return 0; }\n')
            binary = root / 'sleeper'
            subprocess.run(['cc', str(source), '-o', str(binary)], check=True)
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(run(binary, root, 1), -15)
            record = json.loads((root / 'logs/latest.process.json').read_text())
            self.assertFalse(Path('/proc', str(record['pid'])).exists())
            self.assertIn('"reason": "deadline"', output.getvalue())
            self.assertIn('WOL_SAMPLE', output.getvalue())

    def test_bad_budget_launches_nothing(self):
        with self.assertRaises(ValueError):
            run('/nonexistent', '/nonexistent', 0)

    def test_bad_run_id_is_rejected_before_launch(self):
        previous = os.environ.get('WOL_RUN_ID')
        os.environ['WOL_RUN_ID'] = '../outside'
        try:
            with self.assertRaises(ValueError):
                run('/nonexistent', '/nonexistent', 1)
        finally:
            if previous is None:
                os.environ.pop('WOL_RUN_ID', None)
            else:
                os.environ['WOL_RUN_ID'] = previous

    def test_already_exited_children_are_reported_without_traceback(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / 'logs').mkdir()
            for _ in range(12):
                with contextlib.redirect_stdout(io.StringIO()) as output:
                    self.assertEqual(run('/bin/true', root, 1), 0)
                self.assertIn('"reason": "exited"', output.getvalue())

    def test_identity_guard_is_not_stripped_in_optimized_python(self):
        source = (Path(__file__).resolve().parent / 'port/westofloathing/bounded_run.py').read_text()
        self.assertNotIn('assert os.path.samefile', source)


if __name__ == '__main__':
    unittest.main()

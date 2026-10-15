#!/usr/bin/env python3
import importlib.util
from pathlib import Path
import unittest

class BenchmarkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        p = Path(__file__).with_name('wol_memory_benchmark.py')
        cls.m = None
        if p.exists():
            spec = importlib.util.spec_from_file_location('benchmark', p)
            assert spec and spec.loader
            cls.m = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(cls.m)

    def module(self):
        self.assertIsNotNone(self.m, 'benchmark not implemented')
        assert self.m is not None
        return self.m

    def test_frame_counter_gaps_are_not_lost(self):
        m = self.module()
        self.assertEqual(m.frame_rate('MOMO_FRAME frame=10 ns=1000000000\nMOMO_FRAME frame=30 ns=2000000000'), 20)

    def test_png_readiness_rejects_black_even_when_capture_succeeds(self):
        m=self.module()
        import struct,zlib,tempfile
        def png(rgb):
            def chunk(tag,payload):
                return struct.pack('>I',len(payload))+tag+payload+struct.pack('>I',zlib.crc32(tag+payload))
            return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',2,2,8,2,0,0,0))+chunk(b'IDAT',zlib.compress((b'\0'+bytes(rgb)*2)*2))+chunk(b'IEND',b'')
        with tempfile.TemporaryDirectory() as td:
            p=Path(td)/'frame.png'
            p.write_bytes(png([0,0,0]))
            self.assertFalse(m.png_nonblack(p))
            p.write_bytes(png([200,200,200]))
            self.assertTrue(m.png_nonblack(p))

    def test_menu_capture_retries_before_claiming_cleanup(self):
        m = self.module()
        calls=[]
        def runner(args, **kwargs):
            calls.append(args)
            return type('Result', (), {'returncode': 1 if len(calls)==1 else 0})()
        m.capture_menu(Path('/unused.png'), runner=runner, sleeper=lambda seconds: None, validator=lambda path: True)
        self.assertEqual(len(calls), 2)

    def test_menu_capture_failure_stays_a_failure(self):
        m = self.module()
        def runner(args, **kwargs):
            return type('Result', (), {'returncode': 1})()
        with self.assertRaises(RuntimeError):
            m.capture_menu(Path('/unused.png'), attempts=2, runner=runner, sleeper=lambda seconds: None)

    def test_log_archive_failure_does_not_skip_owner_save_restore(self):
        m = self.module()
        import hashlib,json,tempfile
        from types import SimpleNamespace
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)/'port'
            save=root/'save-laboratory'
            save.mkdir(parents=True)
            (save/'slot.json').write_text('owner fixture')
            (root/'logs').mkdir()
            (root/'logs/latest.log').write_text('fixture log')
            (root/'wol-horizon').write_bytes(b'fixture, never executed')
            (root/'wol-romfs.section').write_bytes(b'fixture, never deployed')
            harness=Path(td)/'session.py'
            harness.write_text('# fixture, never executed')
            layout=Path(td)/'layout.json'
            layout.write_text(json.dumps({'elf_sha256':hashlib.sha256((root/'wol-horizon').read_bytes()).hexdigest()}))
            control=Path(td)/'controlled'
            control.mkdir()
            (control/'slot.json').write_text('controlled fixture')
            args=SimpleNamespace(root=root,out=Path(td)/'out',label='fixture',layout=layout,
                session_tool=harness,control_save=control,cold=False,seconds=1,gate=False)
            watcher=SimpleNamespace(wait=lambda **kwargs: 0)
            with patch.object(m,'pids',side_effect=lambda name: [1] if name=='MainUI' else []), \
                 patch.object(m.subprocess,'Popen',return_value=watcher), \
                 patch.object(m.subprocess,'run',side_effect=RuntimeError('fixture startup failure')), \
                 patch.object(m.shutil,'copy2',side_effect=OSError('fixture archive ENOSPC')), \
                 patch.object(m,'capture_menu'), patch.object(m.os,'sync'):
                with self.assertRaises(Exception):
                    m.run(args)
            self.assertEqual((save/'slot.json').read_text(),'owner fixture')

    def make_run_fixture(self, td):
        import hashlib,json
        from types import SimpleNamespace
        root=Path(td)/'port'
        save=root/'save-laboratory'
        save.mkdir(parents=True)
        (save/'slot.json').write_text('owner fixture')
        (root/'logs').mkdir()
        (root/'logs/latest.log').write_text('fixture log')
        (root/'wol-horizon').write_bytes(b'fixture, never executed')
        (root/'wol-romfs.section').write_bytes(b'fixture, never deployed')
        harness=Path(td)/'session.py'
        harness.write_text('# fixture, never executed')
        layout=Path(td)/'layout.json'
        layout.write_text(json.dumps({'elf_sha256':hashlib.sha256((root/'wol-horizon').read_bytes()).hexdigest()}))
        control=Path(td)/'controlled'
        control.mkdir()
        (control/'slot.json').write_text('controlled fixture')
        args=SimpleNamespace(root=root,out=Path(td)/'out',label='fixture',layout=layout,
            session_tool=harness,control_save=control,cold=False,seconds=1,gate=False)
        return args,save

    def test_observer_shutdown_error_does_not_skip_save_restore(self):
        m=self.module()
        import tempfile
        from types import SimpleNamespace
        from unittest.mock import patch
        def fail_wait(**kwargs):
            raise OSError('fixture observer shutdown failure')
        with tempfile.TemporaryDirectory() as td:
            args,save=self.make_run_fixture(td)
            watcher=SimpleNamespace(wait=fail_wait)
            with patch.object(m,'pids',side_effect=lambda name:[1] if name=='MainUI' else []), \
                 patch.object(m.subprocess,'Popen',return_value=watcher), \
                 patch.object(m.subprocess,'run',side_effect=RuntimeError('fixture startup failure')), \
                 patch.object(m,'capture_menu'),patch.object(m.os,'sync'):
                with self.assertRaises(Exception):m.run(args)
            self.assertEqual((save/'slot.json').read_text(),'owner fixture')

    def test_unowned_runtime_preserves_backup_and_marks_pending_recovery(self):
        m=self.module()
        import json,tempfile
        from types import SimpleNamespace
        from unittest.mock import patch
        calls=[]
        def pids(name):
            if name=='MainUI':return [1]
            calls.append(name)
            return [] if len(calls)==1 else [2222]
        with tempfile.TemporaryDirectory() as td:
            args,save=self.make_run_fixture(td)
            watcher=SimpleNamespace(wait=lambda **kwargs:0)
            with patch.object(m,'pids',side_effect=pids), \
                 patch.object(m.subprocess,'Popen',return_value=watcher), \
                 patch.object(m.subprocess,'run',side_effect=RuntimeError('fixture startup failure')), \
                 patch.object(m,'capture_menu'),patch.object(m.os,'sync'):
                with self.assertRaises(Exception):m.run(args)
            self.assertEqual((save/'slot.json').read_text(),'controlled fixture')
            self.assertEqual((args.out/'owner-save/slot.json').read_text(),'owner fixture')
            r=json.loads((args.out/'receipt.json').read_text())
            self.assertIs(r['owner_save_restore_pending'],True)
            self.assertIs(r['cleanup_verified'],False)

    def test_disagreeing_status_and_rollup_stay_separate(self):
        m = self.module()
        rows = [dict(t=0, process={'cpu_ticks':0,'majflt':0}, status={'VmRSS':500,'VmSwap':900,'VmHWM':800}, rollup={'Pss':300,'SwapPss':600}, meminfo={'MemAvailable':100,'CmaFree':20}, vmstat={}),
                dict(t=2, process={'cpu_ticks':20,'majflt':2}, status={'VmRSS':700,'VmSwap':800,'VmHWM':900}, rollup={'Pss':400,'SwapPss':650}, meminfo={'MemAvailable':80,'CmaFree':10}, vmstat={})]
        s = m.summarize(rows, hz=100, page=4096)
        self.assertEqual(s['mean_status_RSS_KiB'], 600)
        self.assertEqual(s['end_PSS_plus_SwapPSS_KiB'], 1050)
        self.assertEqual(s['major_faults_per_s'], 1)
        self.assertEqual(s['min_MemAvailable_KiB'], 80)
        self.assertNotIn('total_gpu_plus_pss', s)

if __name__ == '__main__':
    unittest.main()

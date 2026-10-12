import pathlib
import subprocess
import unittest

ROOT = pathlib.Path(__file__).resolve().parent

class NativeTests(unittest.TestCase):
    def run_case(self, name):
        return subprocess.run(['qemu-aarch64-static', str(ROOT/'wol-native-probe'), '--selftest',name],capture_output=True,text=True,timeout=15)

    def test_guest_tick_trap_returns_nonzero(self):
        result=self.run_case('tick')
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertIn('SELFTEST PASS tick',result.stdout)

    def test_guest_tls_isolated_from_host(self):
        result=self.run_case('tls')
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertIn('SELFTEST PASS tls',result.stdout)

    def test_guest_unknown_svc_stops_explicitly(self):
        result=self.run_case('unknown')
        self.assertEqual(result.returncode,70,result.stdout+result.stderr)
        self.assertIn('UNSUPPORTED_SVC svc=0x7f',result.stdout)

    def test_guest_bootstrap_thread_has_main_handle(self):
        result=self.run_case('tls-thread')
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertIn('SELFTEST PASS tls-thread',result.stdout)

    def test_process_key_signal_without_waiters_succeeds(self):
        result=self.run_case('signal')
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertIn('SELFTEST PASS signal',result.stdout)

    def test_getinfo_returns_configured_cpu_mask(self):
        result=self.run_case('getinfo')
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertIn('SELFTEST PASS getinfo',result.stdout)

    def test_getinfo_entropy_uses_host_random_source(self):
        result=self.run_case('entropy')
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertIn('SELFTEST PASS entropy',result.stdout)

    def test_main_thread_priority_query(self):
        result=self.run_case('priority')
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertIn('SELFTEST PASS priority',result.stdout)

    def test_main_thread_id_query(self):
        result=self.run_case('threadid')
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertIn('SELFTEST PASS threadid',result.stdout)

    def test_zero_mutable_tls_does_not_replace_readonly_tls(self):
        result=self.run_case('tls-zero')
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertIn('SELFTEST PASS tls-zero',result.stdout)

    def test_service_manager_port_connects(self):
        result=self.run_case('sm-connect')
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertIn('SELFTEST PASS sm-connect',result.stdout)

    def test_service_manager_cmif_initialize(self):
        result=self.run_case('sm-init')
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertIn('SELFTEST PASS sm-init',result.stdout)

    def test_malformed_sm_ipc_stops(self):
        result=self.run_case('sm-malformed')
        self.assertEqual(result.returncode,71,result.stdout+result.stderr)
        self.assertIn('INVALID_CMIF',result.stdout)

    def test_query_memory_rejects_readonly_output(self):
        result=self.run_case('query-readonly')
        self.assertEqual(result.returncode,71,result.stdout+result.stderr)
        self.assertIn('BAD_GUEST_POINTER',result.stdout)

    def test_query_memory_reports_mapped_region(self):
        result=self.run_case('query')
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        self.assertIn('SELFTEST PASS query',result.stdout)

if __name__=='__main__': unittest.main()

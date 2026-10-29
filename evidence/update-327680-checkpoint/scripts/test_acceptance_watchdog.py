from pathlib import Path
import hashlib,subprocess,tempfile,unittest,os
W=Path(__file__).resolve().parent
class WatchdogBudgetTest(unittest.TestCase):
 def test_bounded_acceptance_run_accepts_600_refuses_601(self):
  with tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR')) as d:
   d=Path(d);(d/'child.c').write_text('int main(void){return 0;}\n');exe=d/'harmless-child'
   subprocess.run(['cc',str(d/'child.c'),'-o',str(exe)],check=True)
   h=hashlib.sha256(exe.read_bytes()).hexdigest()
   for budget,expected in [('600',0),('601',64)]:
    with self.subTest(budget=budget):
     r=subprocess.run(['python3',str(W/'candidate/watchdog.py'),str(exe),h,budget,str(exe)],capture_output=True,text=True,timeout=5)
     self.assertEqual(r.returncode,expected,r.stdout+r.stderr)
if __name__=='__main__':unittest.main()

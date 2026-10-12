import pathlib, subprocess, tempfile, os, unittest, hashlib
ROOT=pathlib.Path(__file__).resolve().parent

@unittest.skipUnless((ROOT/'wol-base/exefs/rtld').exists(),'owner ExeFS integration input absent')
class PrepareTests(unittest.TestCase):
    def test_preparation_reproduces_verified_segments_and_layout(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR')) as tmp:
            out=pathlib.Path(tmp)/'image'
            p=subprocess.run(['python',str(ROOT/'prepare_image.py'),str(ROOT/'wol-base/exefs'),str(out)],capture_output=True,text=True)
            self.assertEqual(p.returncode,0,p.stdout+p.stderr)
            self.assertEqual((out/'native-layout.txt').read_bytes(),(ROOT/'native-layout.txt').read_bytes())
            for source in (ROOT/'wol-base/segments').glob('*.seg'):
                self.assertEqual(hashlib.sha256(source.read_bytes()).digest(),hashlib.sha256((out/'segments'/source.name).read_bytes()).digest())

if __name__=='__main__': unittest.main()

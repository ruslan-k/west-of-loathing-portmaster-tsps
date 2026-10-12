import pathlib,subprocess,tempfile,os,unittest
ROOT=pathlib.Path(__file__).resolve().parent
BASE=pathlib.Path('/mnt/external/Hermes/spikes/wol-switch')
@unittest.skipUnless((BASE/'wol-romfs.json').exists(),'verified owner RomFS input absent')
class HorizonPrepareTests(unittest.TestCase):
    def test_generates_owned_image_and_shader_stub_declared(self):
        with tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR')) as t:
            out=pathlib.Path(t)/'image'
            p=subprocess.run(['python3',str(ROOT/'prepare_horizon_image.py'),str(BASE/'wol-base/exefs'),str(BASE/'wol-npdm.json'),str(BASE/'wol-romfs.json'),str(out)],capture_output=True,text=True)
            self.assertEqual(p.returncode,0,p.stdout+p.stderr)
            h=(out/'image_table.h').read_text()
            self.assertIn('rtld.text.seg',h)
            self.assertIn('WOL_NVN_QUEUE_BUILDER_OFFSET 0',h)
            self.assertIn('main.data.seg',h)
            self.assertIn('LC2_PROGRAM_ID 0x10031b00a4e8000',h)
            g=(out/'megaman_graphics_contract.h').read_text()
            self.assertIn('LC2_NVN_LOOKUP_POINTER',g)
            self.assertTrue((out/'wol-romfs.section').exists())
            self.assertTrue((out/'megaman_lc2_contract.h').exists())
if __name__=='__main__': unittest.main()

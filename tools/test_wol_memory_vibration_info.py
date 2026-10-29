"""HID metadata queries validate handle format, not actuator registration."""
from pathlib import Path
import subprocess
import tempfile
import unittest


class VibrationInfoTests(unittest.TestCase):
    def test_handheld_info_before_activation_and_invalid_handle_refusal(self):
        patch=(Path(__file__).resolve().parents[1]/'runtime/wol-adapter.patch').read_text()
        added='\n'.join(l[1:] for l in patch.splitlines() if l.startswith('+') and not l.startswith('+++'))
        begin='/* WOL_VIBRATION_HANDLE_BEGIN */';end='/* WOL_VIBRATION_HANDLE_END */'
        self.assertTrue(begin in added and end in added,'missing structural vibration handle validator')
        helper=added.split(begin,1)[1].split(end,1)[0]
        self.assertIn('side=hid_vibration_handle_side(handle,pc)',added)
        self.assertTrue('hid_aruid(req,8,pc);unsigned side=hid_vibration_handle_side(read32(req->data),pc)' in added,'actual/mounted queries still incorrectly require actuator activation')
        present='\n'.join(l[1:] for l in patch.splitlines() if l.startswith(('+',' ')) and not l.startswith('+++'))
        guard=present.split('/* WOL_VIBRATION_WRITE_GUARD_BEGIN */',1)[1].split('/* WOL_VIBRATION_WRITE_GUARD_END */',1)[0]
        fixture=r'''
#include <stdint.h>
#include <stdlib.h>
#include <stdio.h>
static void stop(const char *name,uint64_t pc,uint64_t value,int code){(void)pc;(void)value;puts(name);exit(code);}
static struct {unsigned open,count;uint32_t handles[128];} vibration_lists[8]={{1,1,{3}}};
'''+helper+guard+r'''
int main(int argc,char **argv){if(argc<2||argc>3)return 99;uint32_t h=(uint32_t)strtoul(argv[1],NULL,0);printf("%u\n",argc==3?hid_vibration_side(h,0):hid_vibration_handle_side(h,0));return 0;}
'''
        with tempfile.TemporaryDirectory() as d:
            c=Path(d)/'hid.c';binary=Path(d)/'hid';c.write_text(fixture)
            subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror',str(c),'-o',str(binary)],check=True,capture_output=True)
            for handle,side in [('0x3','0'),('0x10003','1'),('0x2004','0'),('0x12004','1')]:
                out=subprocess.run([str(binary),handle],check=True,capture_output=True,text=True)
                self.assertEqual(out.stdout.strip(),side)
            for handle in ('0x1000003','0x2','0x22004','0x2104','0x10006','0x7'):
                out=subprocess.run([str(binary),handle],capture_output=True,text=True)
                self.assertEqual(out.returncode,20,handle)
                self.assertEqual(out.stdout.strip(),'UNSUPPORTED_VIBRATION_HANDLE')
            registered=subprocess.run([str(binary),'0x3','write'],check=True,capture_output=True,text=True)
            self.assertEqual(registered.stdout.strip(),'0')
            unregistered=subprocess.run([str(binary),'0x12004','write'],capture_output=True,text=True)
            self.assertEqual(unregistered.returncode,20)
            self.assertEqual(unregistered.stdout.strip(),'HID_VIBRATION_ROUTE_REQUIRED')


if __name__=='__main__':unittest.main()

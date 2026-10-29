"""Vibration route guard: a handheld handle must not fail the whole guest.

Measured on device (run rect-a1): the title's Continue press issues
SetVibrationValues for handle 0x12004 (style 4, player 0x20 handheld, device 1)
without any SendVibrationValues registration session, and the guard stopped the
runtime with HID_VIBRATION_ROUTE_REQUIRED / rc=20 after 129 s. The handheld
actuator has no registration list in this title, so that exact handle class is
accepted as implicitly mounted while every other unregistered handle still
fails closed.
"""
from pathlib import Path
import subprocess
import tempfile
import unittest


class ImplicitHandheldVibrationTests(unittest.TestCase):
    def _block(self):
        patch = (Path(__file__).resolve().parents[1] / 'runtime/wol-adapter.patch').read_text()
        # Marker lines and the function signature can be context lines of the hunk, not additions:
        # keep both '+' and ' ' lines so the extracted block compiles as written in the tree.
        added = '\n'.join(l[1:] for l in patch.splitlines()
                          if l[:1] in ('+', ' ') and not l.startswith('+++'))
        begin = '/* WOL_VIBRATION_WRITE_GUARD_BEGIN */'
        end = '/* WOL_VIBRATION_WRITE_GUARD_END */'
        self.assertIn(begin, added)
        self.assertIn(end, added)
        return added.split(begin, 1)[1].split(end, 1)[0]

    def test_handheld_write_is_implicit_and_other_unregistered_handles_fail_closed(self):
        source = r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <unistd.h>
#include <sys/wait.h>
static void stop(const char *m,uint64_t pc,uint64_t a,int code){(void)pc;(void)a;printf("STOP %s\n",m);exit(code);}
static void __attribute__((unused)) diag_printf(const char *f,...){(void)f;}
struct {unsigned open,count;uint32_t handles[128];} vibration_lists[8];
static unsigned hid_vibration_handle_side(uint32_t handle,uint64_t pc) {
    uint32_t style=handle&255,player=(handle>>8)&255,device=(handle>>16)&255;
    if((handle>>24)||style<3||style>7||(player>7&&player!=0x10&&player!=0x20)||device>1||(style==6&&device)||(style==7&&device!=1))
        stop("UNSUPPORTED_VIBRATION_HANDLE",pc,handle,20);
    return device;
}
''' + self._block() + r'''
static int probe(uint32_t handle){
    fflush(stdout);
    pid_t p=fork();
    if(p==0){hid_vibration_side(handle,0);printf("ACCEPT 0x%x\n",handle);fflush(stdout);_exit(0);}
    int st=0;waitpid(p,&st,0);
    return WIFEXITED(st)?WEXITSTATUS(st):99;
}
int main(void){
    vibration_lists[0].open=1;vibration_lists[0].handles[0]=0x3;vibration_lists[0].count=1;
    int rc_registered=probe(0x3);
    int rc_handheld=probe(0x12004);
    int rc_other=probe(0x103);
    printf("RESULT registered=%d handheld=%d other=%d\n",rc_registered,rc_handheld,rc_other);
    return (rc_registered==0 && rc_handheld==0 && rc_other==20)?0:1;
}
'''
        with tempfile.TemporaryDirectory() as d:
            c = Path(d) / 'vib.c'
            binary = Path(d) / 'vib'
            c.write_text(source)
            subprocess.run(['cc', '-std=gnu11', '-Wall', '-Wextra', '-Werror', str(c), '-o', str(binary)],
                           check=True, capture_output=True)
            run = subprocess.run([str(binary)], text=True, capture_output=True)
        self.assertEqual(run.returncode, 0, run.stdout)
        self.assertIn('handheld=0', run.stdout)
        self.assertIn('other=20', run.stdout)


if __name__ == '__main__':
    unittest.main()

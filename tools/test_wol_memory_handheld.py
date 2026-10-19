#!/usr/bin/env python3
"""Execute the actual handheld-only policy from the published GPL overlay."""
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO=Path(__file__).resolve().parents[1]


def added_header(name):
    patch=(REPO/'runtime/wol-adapter.patch').read_text()
    blocks=patch.split('--- ')
    for block in blocks:
        if '\n+++ b/native/'+name+'\n' in block:
            return '\n'.join(s[1:] for s in block.splitlines() if s.startswith('+') and not s.startswith('+++'))+'\n'
    raise AssertionError('missing published header: '+name)


AW_RELEASE_STUB='#ifndef AW_RELEASE_H\n#define AW_RELEASE_H\n#include <stdlib.h>\nstatic inline int aw_release_mode(void){const char *e=getenv("AW_RELEASE");return e&&e[0]==\'1\'&&!e[1];}\n#endif\n'


class HandheldContract(unittest.TestCase):
    def test_fixed_reply_widths_unknown_command_and_trace_default_off(self):
        header=added_header('wol_handheld.h')
        code=r'''
#include <stdio.h>
#include <stdarg.h> /* release-profile logging helper, stubbed for the standalone probe */
static int diag_printf(const char *fmt,...){va_list a;va_start(a,fmt);int r=vprintf(fmt,a);va_end(a);return r;}
#include <stdint.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <time.h>
#include <assert.h>
'''+header+r'''
int main(int argc,char **argv) {
    (void)argc;(void)argv;
    uint32_t value=99;
    assert(wol_handheld_value(5,&value)==1 && value==0);
    value=99;assert(wol_handheld_value(6,&value)==4 && value==0);
    value=99;assert(wol_handheld_value(60,&value)==0 && value==99);
    assert(wol_handheld_value(999,&value)==0 && value==99);
    for(unsigned i=0;i<300;i++)wol_mode_trace("AM",5,1,0,0,1,0x1234);
    puts("POLICY_OK");
}
'''
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'test.c').write_text(code);(p/'aw_release.h').write_text(AW_RELEASE_STUB)
            subprocess.run(['cc','-std=c11','-D_POSIX_C_SOURCE=200809L','-Wall','-Wextra','-Werror',str(p/'test.c'),'-o',str(p/'test')],check=True)
            for mode,n in ((None,0),('0',0),('bad',0),('1',128)):
                env=dict(os.environ);env.pop('WOL_MODE_TRACE',None)
                if mode is not None:env['WOL_MODE_TRACE']=mode
                # A stray selector cannot affect the immutable policy.
                env['WOL_SWITCH_MODE']='docked'
                r=subprocess.run([str(p/'test')],env=env,text=True,capture_output=True,check=True)
                self.assertEqual(r.stdout.count('WOL_MODE_TRACE endpoint='),n)
                self.assertIn('POLICY_OK',r.stdout)
                if n:self.assertIn('cmd=5 domain=1 value0=0 value1=0 bytes=1',r.stdout)


if __name__=='__main__':unittest.main()

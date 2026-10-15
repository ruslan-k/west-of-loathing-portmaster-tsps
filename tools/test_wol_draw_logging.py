#!/usr/bin/env python3
"""Compile the actual trace/error policy; quiet mode must still query/report GL errors."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile

native=Path(sys.argv[1])
s=(native/'nvn_shaders.h').read_text()
r=(native/'nvn_render.h').read_text()
assert '/* WOL_DRAW_TRACE_BEGIN */' in s, 'successful per-draw logging has no opt-in policy'
policy=s.split('/* WOL_DRAW_TRACE_BEGIN */',1)[1].split('/* WOL_DRAW_TRACE_END */',1)[0]
assert 'getenv("WOL_DRAW_TRACE")' in policy
assert 'glGetError' not in policy, 'query GL errors before deciding whether to print'
for name in ('WOL_CAT_DRAW','WOL_PAIR_BANK','WOL_PAIR_TEX','WOL_PAIR_DRAW'):
    assert 'if(wol_draw_trace_enabled())printf("'+name+' ' in r, name+' success output remains unconditional'
assert 'if(wol_draw_trace_enabled())printf("WOL_PROGRAM_BOUND ' in s
for name in ('WOL_PAIR_BANK_INVALID','WOL_PAIR_DRAW_SKIPPED','WOL_DOWNSAMPLE_BLIT_FBO_INCOMPLETE'):
    assert 'if(wol_draw_trace_enabled())printf("'+name not in r, 'failures must remain visible: '+name
pair=r.split('/* WOL_DRAW_RESULT_BEGIN */',1)[1].split('/* WOL_DRAW_RESULT_END */',1)[0]
blit=r.split('/* WOL_BLIT_RESULT_BEGIN */',1)[1].split('/* WOL_BLIT_RESULT_END */',1)[0]
pre=r'''
#define _POSIX_C_SOURCE 200809L
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <inttypes.h>
typedef unsigned GLenum;
static unsigned queries,pending;
static GLenum glGetError(void){queries++;return pending;}
struct texture {uint64_t id;unsigned name;struct {unsigned width,height;} b;};
'''
main=r'''
int main(void){
    uint64_t count=6;
    struct texture a={.id=1,.name=5,.b={.width=1280,.height=720}};
    struct texture b={.id=2,.name=6,.b={.width=1280,.height=720}};
    struct texture *src=&a,*dst=&b;
    int want=getenv("EXPECT_TRACE")&&!strcmp(getenv("EXPECT_TRACE"),"1");
    assert(wol_draw_trace_enabled()==(unsigned)want);
    /* Configuration is immutable for this process, even if env is changed later. */
    assert(setenv("WOL_DRAW_TRACE",want?"0":"1",1)==0);
    assert(wol_draw_trace_enabled()==(unsigned)want);
    pending=0;
    PAIR
    BLIT
    assert(queries==2);
    pending=0x502;
    PAIR
    BLIT
    assert(queries==4);
    puts("POLICY_OK gl-error-queries=4");
    return 0;
}
'''.replace('PAIR',pair).replace('BLIT',blit)
with tempfile.TemporaryDirectory(prefix='wol-draw-log-',dir=os.environ.get('TMPDIR')) as d:
    path=Path(d);c=path/'trace.c';exe=path/'trace'
    c.write_text(pre+policy+main)
    subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror',str(c),'-o',str(exe)],check=True)
    for value in (None,'0','1','false','true','01'):
        env=dict(os.environ);env.pop('WOL_DRAW_TRACE',None);env['EXPECT_TRACE']='1' if value=='1' else '0'
        if value is not None:env['WOL_DRAW_TRACE']=value
        out=subprocess.check_output([str(exe)],env=env,text=True)
        assert out.count('WOL_DRAW_TRACE detailed=')==1,out
        for prefix in ('WOL_PAIR_DRAW_ISSUED','WOL_DOWNSAMPLE_BLIT'):
            rows=[line for line in out.splitlines() if line.startswith(prefix+' ')]
            assert len(rows)==(2 if value=='1' else 1),(value,prefix,out)
            assert any('glerror=0x502' in line for line in rows),out
        print('PASS trace='+repr(value)+' success-output='+('on' if value=='1' else 'off')+' errors=on queries=4')
print('PASS success-only gates preserve error output and per-draw GL error queries')

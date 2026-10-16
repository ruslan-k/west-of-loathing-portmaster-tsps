#!/usr/bin/env python3
"""Execute actual color-write accounting and sparse cadence against directed cases."""
from pathlib import Path
import os,subprocess,sys,tempfile
native=Path(sys.argv[1]);r=(native/'nvn_render.h').read_text();p=(native/'nvn_present.h').read_text()
assert '/* WOL_COLOR_WRITE_BEGIN */' in r,'translated draws lack successful RGB-write accounting'
helper=r.split('/* WOL_COLOR_WRITE_BEGIN */',1)[1].split('/* WOL_COLOR_WRITE_END */',1)[0]
assert 'wol_color_write_account(nvn_render.target,!wol_skip_139_this&&!p2solid,wol_mask_bits,wol_gl_error);' in r
assert 'wol_color_write_account(dst,src->draws!=0,blit_mask,wol_gl_error);' in r
pair=r.split('/* WOL_DRAW_RESULT_BEGIN */',1)[1].split('/* WOL_DRAW_RESULT_END */',1)[0]
assert pair.index('wol_color_write_account(nvn_render.target')>pair.index('GLenum wol_gl_error=glGetError();')
assert 'unsigned proof=nonblack>=32 && t->draws;' in p,'do not weaken pixel proof to enable cadence'
pre=r'''
#include <stdint.h>
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef unsigned GLenum;
struct nvn_texture {unsigned draws;};
static void stop(const char *s,uint64_t c,uint64_t d,int e){(void)s;(void)c;(void)d;(void)e;abort();}
static uint64_t nvn_caller;
'''
main=r'''
int main(void){
 if(getenv("EXPECT_READBACK_OFF")){
  unsigned off=(unsigned)atoi(getenv("EXPECT_READBACK_OFF"));
  assert(nvn_video_should_sample(1,1,0,0)==(off==2));
  assert(!nvn_video_should_sample(1,600,1,1));
  puts("PASS diagnostic OFF modes must NOT be called periodic health checks");return 0;
 }
 struct nvn_texture t={0};
 wol_color_write_account(NULL,1,15,0);
 wol_color_write_account(&t,0,15,0);assert(t.draws==0); /* skipped */
 wol_color_write_account(&t,1,0,0);assert(t.draws==0); /* stencil only */
 wol_color_write_account(&t,1,8,0);assert(t.draws==0); /* alpha only */
 wol_color_write_account(&t,1,15,0x502);assert(t.draws==0);
 wol_color_write_account(&t,1,1,0);assert(t.draws==1);
 wol_color_write_account(&t,1,15,0);assert(t.draws==2);
 t.draws=~0U;wol_color_write_account(&t,1,15,0);assert(t.draws==~0U);
 struct nvn_texture src={0},dst={0};
 wol_color_write_account(&dst,src.draws!=0,15,0);assert(dst.draws==0);
 wol_color_write_account(&src,1,7,0);wol_color_write_account(&dst,src.draws!=0,15,0);assert(dst.draws==1);
 assert(nvn_video_should_sample(1,1,0,0));
 assert(!nvn_video_should_sample(1,1,1,0));
 assert(nvn_video_should_sample(1,600,1,0));
 assert(nvn_video_should_sample(1,4,1,1));
 assert(!nvn_video_should_sample(1,5,1,1));
 assert(nvn_video_should_sample(0,5,1,0));
 assert(nvn_video_should_capture(1,0));
 assert(!nvn_video_should_capture(5,1));
 assert(nvn_video_should_capture(600,1));
 assert(!nvn_video_capture_ready(1,0,1,1,0,1,4));
 assert(nvn_video_capture_ready(1,1,1,1,0,1,4));
 puts("PASS color-write: skip/stencil/alpha/error excluded, saturation safe, proven copies propagate, sparse/dark sampling retained");
}
'''
with tempfile.TemporaryDirectory(prefix='wol-color-proof-',dir=os.environ.get('TMPDIR')) as d:
 path=Path(d);(path/'test.c').write_text(pre+helper+'\n#include "nvn_video_cadence.h"\n'+main)
 subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-I',str(native),str(path/'test.c'),'-o',str(path/'test')],check=True)
 env=dict(os.environ,COTM_READBACK_PERIOD='600',ZERO_DARK_SAMPLE_EVERY='4');env.pop('T2_READBACK_OFF',None)
 subprocess.run([str(path/'test')],env=env,check=True)
 for mode in ('1','2'):
  subprocess.run([str(path/'test')],env=dict(env,T2_READBACK_OFF=mode,EXPECT_READBACK_OFF=mode),check=True)

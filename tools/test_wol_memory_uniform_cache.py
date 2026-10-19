#!/usr/bin/env python3
"""Compile the real constant-bank cache against data-free GLES fixtures."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from test_wol_memory_astc_postcopy import added_file


class UniformCacheTests(unittest.TestCase):
    def test_default_off_census_exact_bits_program_banks_context_and_error(self):
        overlay=(Path(__file__).resolve().parents[1]/'runtime/wol-adapter.patch').read_text()
        text=added_file(overlay,'nvn_shaders.h')
        self.assertIn('/* WOL_UNIFORM_CACHE_BEGIN */',text,'missing bounded constant redundancy/cache experiment')
        code=text.split('/* WOL_UNIFORM_CACHE_BEGIN */',1)[1].split('/* WOL_UNIFORM_CACHE_END */',1)[0]
        render=added_file(overlay,'nvn_render.h')
        self.assertIn('wol_uniform_upload(&wol_cat_cur->uniform_cache,0,wol_pair_c3_loc,words);',render)
        self.assertIn('wol_uniform_upload(&wol_cat_cur->uniform_cache,1,wol_pair_c3f_loc,fwords);',render)
        self.assertIn('wol_uniform_cache_error(wol_gl_error);',render)
        pre=r'''
#include <stdio.h>
#include <stdarg.h> /* release-profile logging helper, stubbed for the standalone probe */
static int diag_printf(const char *fmt,...){char b[256];va_list a;va_start(a,fmt);int r=vsnprintf(b,sizeof(b),fmt,a);va_end(a);(void)r;return 0;}
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <stdlib.h>
#include <assert.h>
typedef int GLint,GLsizei;typedef unsigned GLenum;typedef void *EGLContext;
static EGLContext context=(void*)1;static unsigned writes,context_reads;
static EGLContext eglGetCurrentContext(void){context_reads++;return context;}
static void glUniform1fv(GLint location,GLsizei count,const float *v){assert(location>=0 && count==96 && v);writes++;}
'''
        main=r'''
int main(int argc,char **argv){
 struct wol_uniform_bank_cache a={0},b={0};float v[96]={0};
 if(argc==1){unsetenv("WOL_UNIFORM_CACHE");unsetenv("WOL_UNIFORM_CENSUS");
  wol_uniform_upload(&a,0,10,v);wol_uniform_upload(&a,0,10,v);
  assert(writes==2 && context_reads==0);return 0;}
 unsigned census=!strcmp(argv[1],"census");
 setenv(census?"WOL_UNIFORM_CENSUS":"WOL_UNIFORM_CACHE","1",1);
 wol_uniform_upload(&a,0,10,v);wol_uniform_upload(&a,0,10,v);
 assert(writes==(census?2U:1U));assert(wol_uniform_state.redundant==1);
 unsigned before=writes;
 v[0]=1;wol_uniform_upload(&a,0,10,v);assert(writes==before+1);
 wol_uniform_upload(&a,1,20,v);assert(writes==before+2);
 wol_uniform_upload(&b,0,10,v);assert(writes==before+3);
 /* Bitwise equality handles NaN payloads without treating them as equal values. */
 uint32_t bits=0x7fc00001;memcpy(v,&bits,4);wol_uniform_upload(&a,0,10,v);
 before=writes;wol_uniform_upload(&a,0,10,v);assert(writes==before+(census?1U:0U));
 bits=0x7fc00002;memcpy(v,&bits,4);before=writes;
 wol_uniform_upload(&a,0,10,v);assert(writes==before+1);
 /* Shared contexts invalidate all programs on every observed context change. */
 context=(void*)2;before=writes;wol_uniform_upload(&a,0,10,v);assert(writes==before+1);
 context=(void*)1;before=writes;wol_uniform_upload(&a,0,10,v);assert(writes==before+1);
 wol_uniform_cache_error(0x502);before=writes;
 wol_uniform_upload(&a,0,10,v);assert(writes==before+1);
 before=writes;wol_uniform_upload(&a,0,11,v);assert(writes==before+1);
 before=writes;wol_uniform_upload(&a,0,-1,v);assert(writes==before);
 context=NULL;before=writes;wol_uniform_upload(&a,0,10,v);wol_uniform_upload(&a,0,10,v);assert(writes==before+2);
 wol_uniform_cache_report(300);puts("UNIFORM_CACHE_CONTRACT_OK");return 0;}
'''
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);(p/'t.c').write_text(pre+code+main)
            cc=shutil.which('cc') or shutil.which('gcc');assert cc
            subprocess.run([cc,'-std=gnu11','-O2','-Wall','-Wextra','-Werror',str(p/'t.c'),'-o',str(p/'t')],check=True)
            subprocess.run([str(p/'t')],check=True)
            for mode in ('census','enabled'):
                result=subprocess.run([str(p/'t'),mode],capture_output=True,text=True,check=True)
                self.assertIn('UNIFORM_CACHE_CONTRACT_OK',result.stdout)


if __name__=='__main__':
    unittest.main()

#!/usr/bin/env python3
"""Compile the actual bounded upload timing wrapper; verify default-off pixel/order API."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from test_wol_memory_astc_postcopy import added_file


def c_function(source, name):
    start=source.index(name)
    start=source.rfind('\n',0,start)+1
    depth=0
    for i in range(source.index('{',start),len(source)):
        depth+=(source[i]=='{')-(source[i]=='}')
        if depth==0:return source[start:i+1]
    raise ValueError(name)


class UploadTiming(unittest.TestCase):
    def test_pixels_unchanged_and_finish_only_in_bounded_opt_in_diagnostic(self):
        patch=(Path(__file__).resolve().parents[1]/'runtime/wol-adapter.patch').read_text()
        source=added_file(patch,'nvn_textures.h')
        funcs=c_function(source,'wol_upload_clock(')+'\n'+c_function(source,'wol_texture_upload(')
        pre=r'''
#include <stdint.h>
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <assert.h>
#define GL_TEXTURE_2D 1
#define GL_RGBA 2
struct nvn_texture {uint64_t id;struct {unsigned format;} b;};
static unsigned wol_pbo_upload(struct nvn_texture *t,unsigned l,unsigned w,unsigned h,unsigned k,const void *p){(void)t;(void)l;(void)w;(void)h;(void)k;(void)p;return 0;}
static unsigned finishes,uploads;static const unsigned char image[4]={1,2,3,4};
static unsigned zero_bc_srgb(unsigned f){(void)f;return 0;}
static unsigned nvn_texture_upload_bytes(unsigned t){assert(t==3);return 4;}
static void glFinish(void){finishes++;}
static void glTexSubImage2D(unsigned t,unsigned l,int x,int y,unsigned w,unsigned h,unsigned f,unsigned k,const void *p){assert(t==GL_TEXTURE_2D && l==0 && x==0 && y==0 && w==1 && h==1 && f==GL_RGBA && k==3 && p==image);uploads++;}
'''
        main=r'''
int main(int argc,char **argv){(void)argv;
 if(argc>1)setenv("WOL_UPLOAD_TIMING","1",1);else unsetenv("WOL_UPLOAD_TIMING");
 struct nvn_texture t={.id=460,.b={.format=0x25}};
 for(unsigned i=0;i<500;i++)wol_texture_upload(&t,0,1,1,3,image);
 assert(uploads==500);assert(finishes==(argc>1?6:0));puts("UPLOAD_TIMING_OK");return 0;
}
'''
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);c=root/'t.c';c.write_text(pre+funcs+main)
            cc=shutil.which('cc') or shutil.which('gcc');assert cc
            subprocess.run([cc,'-std=gnu11','-O2','-Wall','-Wextra','-Werror',str(c),'-o',str(root/'t')],check=True)
            for args in ([],['on']):
                r=subprocess.run([str(root/'t'),*args],capture_output=True,text=True,check=True)
                self.assertIn('UPLOAD_TIMING_OK',r.stdout)
                self.assertEqual(r.stdout.count('WOL_UPLOAD_TIMING id='),3 if args else 0)


if __name__=='__main__':
    unittest.main()

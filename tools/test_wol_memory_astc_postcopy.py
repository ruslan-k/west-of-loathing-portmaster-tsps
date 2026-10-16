#!/usr/bin/env python3
"""Synthetic acceptance seam: post-copy eligibility and full-image RGBA fallback.
Tests compile the actual added C functions from the published overlay, not replicas.
"""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


def added_file(patch,name):
    part=patch.split('--- a/native/'+name+'\n',1)[1].split('\n--- ',1)[0]
    return '\n'.join(l[1:] for l in part.splitlines() if l.startswith('+') and not l.startswith('+++'))


class PostCopyTests(unittest.TestCase):
    def test_complete_only_default_off_and_full_restore_before_partial_write(self):
        p=Path(__file__).resolve().parents[1]/'runtime/wol-adapter.patch'
        patch=p.read_text();header=added_file(patch,'nvn_astc_cache.h')
        gate=header.split('static unsigned nvn_astc_postcopy_enabled',1)[1].split('/* WOL_ASTC_POSTCOPY_END */',1)[0]
        gate='static unsigned nvn_astc_postcopy_enabled'+gate
        src=added_file(patch,'nvn_textures.h');start=src.index('static void nvn_astc_restore_rgba')
        depth=0;finish=None
        for i in range(src.index('{',start),len(src)):
            depth+=(src[i]=='{')-(src[i]=='}')
            if depth==0:finish=i+1;break
        restore=src[start:finish]
        pre=r'''
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <assert.h>
#include <inttypes.h>
typedef unsigned GLenum,GLuint;typedef int GLint;
#define GL_TEXTURE_BINDING_2D 1
#define GL_UNPACK_ALIGNMENT 2
#define GL_TEXTURE_2D 3
#define GL_RGBA 4
#define GL_UNSIGNED_BYTE 5
struct nvn_texture {uint64_t id;unsigned composition_target_seen,draws,host_scaled,host_half,packaged_lazy,normal_unmaterialized,zero_backend_deferred,astc_from_cache,name;void *cpu_snapshot;
 struct {unsigned width,height,levels,target,depth,samples,format,packaged_layout,packaged;} b;};
static uint64_t nvn_caller;
static unsigned zero_bc_bytes(unsigned f){return f==0x41?8:f==0x44?16:0;}
static void stop(const char *s,uint64_t pc,uint64_t v,unsigned c){(void)pc;(void)v;(void)c;fprintf(stderr,"%s",s);abort();}
static unsigned char uploaded[64];static unsigned uploads;static GLint bound=99,align=8;
static void zero_texture_bc_pixels(struct nvn_texture *t,unsigned level,const uint32_t *box,void *p,size_t n){(void)t;assert(level==0 && !box);for(size_t i=0;i<n;i++)((unsigned char *)p)[i]=(unsigned char)(i+10);}
static void glGetIntegerv(GLenum k,GLint *v){*v=k==GL_UNPACK_ALIGNMENT?align:bound;}
static void glBindTexture(GLenum k,GLuint n){(void)k;bound=n;}
static void glPixelStorei(GLenum k,GLint n){(void)k;align=n;}
static GLenum glGetError(void){return 0;}
static void glTexImage2D(GLenum target,GLint level,GLint internal,GLint w,GLint h,GLint border,GLenum format,GLenum type,const void *pixels){(void)internal;(void)border;(void)type;assert(target==GL_TEXTURE_2D && level==0 && format==GL_RGBA && pixels);assert(w*h*4<=64);memcpy(uploaded,pixels,(size_t)w*h*4);uploads++;}
'''
        main=r'''
int main(int argc,char **argv){
 (void)argv;struct nvn_texture t={.id=469,.b={.width=4,.height=4,.levels=1,.target=1,.depth=1,.format=0x41}};
 uint32_t box[6]={0,0,0,4,4,1};
 if(argc==1){unsetenv("WOL_ASTC_POSTCOPY");setenv("WOL_ASTC_POSTCOPY_ID","469",1);assert(!nvn_astc_postcopy_allowed(&t,0,box));return 0;}
 setenv("WOL_ASTC_POSTCOPY","1",1);setenv("WOL_ASTC_POSTCOPY_ID","469",1);assert(nvn_astc_postcopy_allowed(&t,0,box));
 assert(!nvn_astc_postcopy_allowed(&t,1,box));box[3]=2;assert(!nvn_astc_postcopy_allowed(&t,0,box));box[3]=4;
 t.b.levels=2;assert(!nvn_astc_postcopy_allowed(&t,0,box));t.b.levels=1;
 t.b.samples=4;assert(!nvn_astc_postcopy_allowed(&t,0,box));t.b.samples=0;
 t.draws=1;assert(!nvn_astc_postcopy_allowed(&t,0,box));t.draws=0;
 t.composition_target_seen=1;assert(!nvn_astc_postcopy_allowed(&t,0,box));t.composition_target_seen=0;
 t.b.format=0x42;assert(!nvn_astc_postcopy_allowed(&t,0,box));t.b.format=0x41;
 setenv("WOL_ASTC_POSTCOPY_ID","470",1);assert(!nvn_astc_postcopy_allowed(&t,0,box));
 setenv("WOL_ASTC_POSTCOPY_ID","469bad",1);assert(!nvn_astc_postcopy_allowed(&t,0,box));
 t.astc_from_cache=1;t.name=7;nvn_astc_restore_rgba(&t,"partial-test");
 assert(uploads==1 && !t.astc_from_cache && bound==99 && align==8);
 for(unsigned i=0;i<64;i++)assert(uploaded[i]==i+10);
 nvn_astc_restore_rgba(&t,"already-rgba");assert(uploads==1);
 puts("POSTCOPY_CONTRACT_OK");return 0;
}
'''
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);(root/'test.c').write_text(pre+gate+restore+main)
            cc=shutil.which('cc') or shutil.which('gcc');assert cc
            subprocess.run([cc,'-std=gnu11','-O2','-Wall','-Wextra','-Werror',str(root/'test.c'),'-o',str(root/'test')],check=True)
            subprocess.run([str(root/'test')],check=True)
            result=subprocess.run([str(root/'test'),'enabled'],capture_output=True,text=True,check=True)
            self.assertIn('POSTCOPY_CONTRACT_OK',result.stdout)


if __name__=='__main__':
    unittest.main()

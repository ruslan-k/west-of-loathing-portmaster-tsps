#!/usr/bin/env python3
"""Compile the real NVN stencil decoder and require it in substituted draws."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
s=Path(sys.argv[1]).read_text()
code=s.split('static GLenum nvn_stencil_operation(',1)[1].split('static struct nvn_descriptor *nvn_render_descriptor',1)[0]
code='static GLenum nvn_stencil_operation('+code
preamble=r'''
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <assert.h>
typedef unsigned GLenum;
enum {GL_KEEP=1,GL_ZERO,GL_REPLACE,GL_INCR,GL_DECR,GL_INVERT,GL_INCR_WRAP,GL_DECR_WRAP,
GL_STENCIL_TEST,GL_FRONT,GL_BACK,GL_NEVER=512};
#define NCS_STENCIL_ENABLE 7
struct tex {struct {unsigned format;} b;};
struct {unsigned depth_state[2];struct tex *depth;
uint8_t stencil_ref[2],stencil_compare[2],stencil_write[2],stencil_known[2];} nvn_render;
unsigned nvn_caller,enabled;
struct {unsigned func,ref,compare,write,fail,zfail,zpass;} faces[2];
void stop(const char *s,unsigned pc,unsigned d,int rc){(void)pc;(void)d;(void)rc;fprintf(stderr,"STOP %s\n",s);abort();}
void nvn_render_cap(unsigned slot,unsigned cap,unsigned on){assert(slot==7&&cap==GL_STENCIL_TEST);enabled=on;}
void glStencilFuncSeparate(unsigned side,unsigned f,unsigned r,unsigned m){unsigned i=side==GL_BACK;faces[i].func=f;faces[i].ref=r;faces[i].compare=m;}
void glStencilMaskSeparate(unsigned side,unsigned m){faces[side==GL_BACK].write=m;}
void glStencilOpSeparate(unsigned side,unsigned f,unsigned zf,unsigned zp){unsigned i=side==GL_BACK;faces[i].fail=f;faces[i].zfail=zf;faces[i].zpass=zp;}
'''
cases=r'''
int main(void){
 struct tex depth={{0x35}};nvn_render.depth=&depth;
 for(unsigned i=0;i<2;i++){nvn_render.stencil_known[i]=7;nvn_render.stencil_ref[i]=1;nvn_render.stencil_compare[i]=255;nvn_render.stencil_write[i]=255;}
 nvn_render.depth_state[0]=4;nvn_render.depth_state[1]=0x13181318;
 nvn_render_stencil();assert(enabled);
 for(unsigned i=0;i<2;i++){assert(faces[i].func==GL_NEVER+7&&faces[i].ref==1&&faces[i].compare==255&&faces[i].write==255);assert(faces[i].fail==GL_KEEP&&faces[i].zfail==GL_KEEP&&faces[i].zpass==GL_REPLACE);}
 puts("PASS mask writer: ALWAYS + REPLACE for both faces");
 nvn_render.depth_state[1]=0x11131113;nvn_render.stencil_write[0]=nvn_render.stencil_write[1]=0;
 nvn_render_stencil();
 for(unsigned i=0;i<2;i++){assert(faces[i].func==GL_NEVER+2&&faces[i].write==0&&faces[i].zpass==GL_KEEP);}
 puts("PASS portrait consumer: EQUAL ref=1, read-only stencil");
 nvn_render.depth_state[0]=0;nvn_render.depth=NULL;nvn_render_stencil();assert(!enabled);
 puts("PASS unmasked gameplay disables stencil without requiring an attachment");
}
'''
with tempfile.TemporaryDirectory(prefix='wol-stencil-',dir=os.environ.get('TMPDIR')) as tmp:
 c=Path(tmp)/'probe.c';c.write_text(preamble+code+cases);exe=Path(tmp)/'probe'
 subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror',str(c),'-o',str(exe)],check=True)
 subprocess.run([str(exe)],check=True)
hook=s.split('static void nvn_render_draw_inner',1)[1].split('        skipped++;',1)[0]
assert 'nvn_render_stencil();' in hook,'substituted draws bypass the guest stencil state: portrait mask cannot clip its character'
assert 'nvn_render_state.valid&=~(1u<<NCS_STENCIL_ENABLE)' in hook,'stencil enable must resync after non-cached helper passes'
print('PASS substituted draws replay stencil and invalidate cached enable')

#!/usr/bin/env python3
"""Exercise the actual opt-in PBO helper with data-free GL/fence fixtures."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from test_wol_memory_astc_postcopy import added_file


class PboLifecycle(unittest.TestCase):
    def test_default_off_busy_fallback_retired_reuse_and_context_identity(self):
        text=added_file((Path(__file__).resolve().parents[1]/'runtime/wol-adapter.patch').read_text(),'nvn_textures.h')
        code=text.split('/* WOL_PBO_UPLOAD_BEGIN */',1)[1].split('/* WOL_PBO_UPLOAD_END */',1)[0]
        pre=r'''
#include <stdio.h>
#include <stdint.h>
#include <inttypes.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
typedef unsigned GLenum,GLuint,GLbitfield;typedef int GLint,GLsizei;typedef unsigned char GLboolean;typedef intptr_t GLintptr,GLsizeiptr;typedef void *EGLContext;
#define GL_TEXTURE_2D 0xde1
#define GL_RGBA 0x1908
#define GL_UNSIGNED_BYTE 0x1401
#define GL_STREAM_DRAW 0x88e0
struct nvn_texture {uint64_t id;struct{unsigned format;}b;};
static unsigned bound,uploads,deletes,generated,ready,next_fence=1;static EGLContext context=(void*)1;
static unsigned char buffers[2][3686400],image[3686400];
static EGLContext eglGetCurrentContext(void){return context;}
static void glGetIntegerv(GLenum k,GLint *v){assert(k==0x88ef);*v=(GLint)bound;}
static void glGenBuffers(GLsizei n,GLuint *v){assert(n==2);v[0]=11;v[1]=12;generated+=2;}
static void glBindBuffer(GLenum t,GLuint n){assert(t==0x88ec);bound=n;}
static void glBufferData(GLenum t,GLsizeiptr n,const void *p,GLenum use){assert(t==0x88ec && n==3686400 && !p && use==GL_STREAM_DRAW && bound>=11 && bound<=12);}
static GLenum glGetError(void){return 0;}
static void *map(GLenum t,GLintptr off,GLsizeiptr n,GLbitfield bits){assert(t==0x88ec && !off && n==3686400 && bits==2);return buffers[bound-11];}
static GLboolean unmap(GLenum t){assert(t==0x88ec);return 1;}
static void *fence(GLenum t,GLbitfield b){assert(t==0x9117 && !b);return (void*)(uintptr_t)next_fence++;}
static GLenum wait_sync(void *s,GLbitfield b,uint64_t timeout){assert(s && !b && !timeout);return ready?0x911c:0x911b;}
static void delete_sync(void *s){assert(s && ready);deletes++;}
static void *eglGetProcAddress(const char *s){
 if(!strcmp(s,"glMapBufferRange"))return (void*)map;
 if(!strcmp(s,"glUnmapBuffer"))return (void*)unmap;
 if(!strcmp(s,"glFenceSync"))return (void*)fence;
 if(!strcmp(s,"glClientWaitSync"))return (void*)wait_sync;
 if(!strcmp(s,"glDeleteSync"))return (void*)delete_sync;
 abort();}
static uint64_t nvn_caller;
static void stop(const char *s,uint64_t a,uint64_t b,unsigned c){(void)a;(void)b;(void)c;fprintf(stderr,"%s",s);abort();}
static void glTexSubImage2D(GLenum t,GLint l,GLint x,GLint y,GLsizei w,GLsizei h,GLenum f,GLenum k,const void *p){assert(t==GL_TEXTURE_2D && !l && !x && !y && w==1280 && h==720 && f==GL_RGBA && k==GL_UNSIGNED_BYTE && !p);assert(!memcmp(buffers[bound-11],image,sizeof(image)));uploads++;}
'''
        main=r'''
int main(int argc,char **argv){(void)argv;struct nvn_texture t={.id=460,.b={.format=0x25}};
 if(argc==1){unsetenv("WOL_PBO_UPLOAD");assert(!wol_pbo_upload(&t,0,1280,720,GL_UNSIGNED_BYTE,image));assert(!generated);return 0;}
 setenv("WOL_PBO_UPLOAD","1",1);memset(image,31,sizeof(image));
 assert(wol_pbo_upload(&t,0,1280,720,GL_UNSIGNED_BYTE,image));assert(!bound);
 memset(image,42,sizeof(image));assert(wol_pbo_upload(&t,0,1280,720,GL_UNSIGNED_BYTE,image));assert(!bound);
 assert(!wol_pbo_upload(&t,0,1280,720,GL_UNSIGNED_BYTE,image));assert(uploads==2 && deletes==0);
 ready=1;assert(wol_pbo_upload(&t,0,1280,720,GL_UNSIGNED_BYTE,image));assert(uploads==3 && deletes==1 && generated==2 && !bound);
 context=(void*)2;assert(!wol_pbo_upload(&t,0,1280,720,GL_UNSIGNED_BYTE,image));assert(uploads==3 && deletes==1);
 puts("PBO_LIFETIME_OK");return 0;}
'''
        with tempfile.TemporaryDirectory() as td:
            r=Path(td);(r/'t.c').write_text(pre+code+main)
            cc=shutil.which('cc') or shutil.which('gcc');assert cc
            subprocess.run([cc,'-std=gnu11','-O2','-Wall','-Wextra','-Werror',str(r/'t.c'),'-o',str(r/'t')],check=True)
            subprocess.run([str(r/'t')],check=True)
            got=subprocess.run([str(r/'t'),'enabled'],capture_output=True,text=True,check=True)
            self.assertIn('PBO_LIFETIME_OK',got.stdout)


if __name__=='__main__':unittest.main()

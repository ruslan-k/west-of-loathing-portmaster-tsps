#!/usr/bin/env python3
"""Actual bounded GPU elapsed-query helper with fake asynchronous driver boundary."""
import os,subprocess,tempfile,unittest
from pathlib import Path
from test_wol_memory_handheld import added_header

AW_RELEASE_STUB='#ifndef AW_RELEASE_H\n#define AW_RELEASE_H\n#include <stdlib.h>\nstatic inline int aw_release_mode(void){const char *e=getenv("AW_RELEASE");return e&&e[0]==\'1\'&&!e[1];}\n#endif\n'


class GpuTimelineContract(unittest.TestCase):
    def test_default_off_no_wait_recycle_and_disjoint(self):
        code=r'''
#include <stdio.h>
#include <stdarg.h> /* release-profile logging helper, stubbed for the standalone probe */
static int diag_printf(const char *fmt,...){va_list a;va_start(a,fmt);int r=vprintf(fmt,a);va_end(a);return r;}
#define _GNU_SOURCE
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include <assert.h>
typedef unsigned GLenum,GLuint;typedef int GLint,GLsizei;
static unsigned begins,ends,deletes,gets,available,disjoint;
static void gen(GLsizei n,GLuint *id){assert(n==1);*id=7;}
static void del(GLsizei n,const GLuint *id){assert(n==1&&*id==7);deletes++;}
static void begin(GLenum e,GLuint id){assert(e==0x88bf&&id==7);begins++;}
static void end(GLenum e){assert(e==0x88bf);ends++;}
static void get(GLuint id,GLenum e,GLuint *v){assert(id==7&&e==0x8867);*v=available;gets++;}
static void get64(GLuint id,GLenum e,uint64_t *v){assert(id==7&&e==0x8866&&available);*v=456000;}
static void integer(GLenum e,GLint *v){assert(e==0x8fbb);*v=disjoint;}
'''+added_header('wol_gpu_timeline.h')+r'''
int main(int argc,char **argv){
 (void)argv;
 struct wol_gpu_timer t={.gen=gen,.del=del,.begin=begin,.end=end,.get=get,.get64=get64,.integer=integer};
 if(argc==1){unsetenv("WOL_GPU_TIMELINE");assert(!wol_gpu_timer_enabled());assert(begins==0);return 0;}
 setenv("WOL_GPU_TIMELINE","1",1);assert(wol_gpu_timer_enabled());
 assert(wol_gpu_timer_begin(&t,120,9,55,1920,1080,(uintptr_t)1));
 assert(!wol_gpu_timer_begin(&t,120,9,55,1920,1080,(uintptr_t)1));
 wol_gpu_timer_end(&t);assert(begins==1&&ends==1);
 assert(!wol_gpu_timer_poll(&t,(uintptr_t)1));assert(gets==1&&deletes==0);
 available=1;assert(wol_gpu_timer_poll(&t,(uintptr_t)1));assert(deletes==1);
 assert(wol_gpu_timer_begin(&t,240,9,55,1280,720,(uintptr_t)1));wol_gpu_timer_end(&t);
 disjoint=1;assert(wol_gpu_timer_poll(&t,(uintptr_t)1));assert(t.discarded==1);
 puts("GPU_TIMELINE_OK");
}
'''
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'test.c').write_text(code);(p/'aw_release.h').write_text(AW_RELEASE_STUB)
            subprocess.run(['cc','-std=gnu11','-O2','-Wall','-Wextra','-Werror',str(p/'test.c'),'-o',str(p/'test')],check=True)
            subprocess.run([str(p/'test')],check=True)
            r=subprocess.run([str(p/'test'),'on'],check=True,capture_output=True,text=True)
            self.assertIn('GPU_TIMELINE_OK',r.stdout)
            self.assertIn('gpu_ns=456000',r.stdout)
if __name__=='__main__':unittest.main()

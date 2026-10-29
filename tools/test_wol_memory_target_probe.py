"""Exercise the opt-in target census with explicit GL dependency stubs."""
from pathlib import Path
import subprocess
import tempfile
import unittest


class TargetProbeTests(unittest.TestCase):
    def test_bounded_opt_in_sampling_restores_framebuffer_state(self):
        patch=(Path(__file__).resolve().parents[1]/'runtime/wol-adapter.patch').read_text()
        added='\n'.join(l[1:] for l in patch.splitlines() if l.startswith('+') and not l.startswith('+++'))
        self.assertTrue('/* WOL_TARGET_PROBE_BEGIN */' in added,'target probe missing')
        block=added.split('/* WOL_TARGET_PROBE_BEGIN */',1)[1].split('/* WOL_TARGET_PROBE_END */',1)[0]
        code=r'''
#define _GNU_SOURCE
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
typedef int GLint;
typedef unsigned GLuint;
#define GL_FRAMEBUFFER 1
#define GL_READ_FRAMEBUFFER 2
#define GL_DRAW_FRAMEBUFFER 3
#define GL_READ_FRAMEBUFFER_BINDING 4
#define GL_DRAW_FRAMEBUFFER_BINDING 5
#define GL_FRAMEBUFFER_BINDING 5
#define GL_READ_BUFFER 6
#define GL_PACK_ALIGNMENT 7
#define GL_COLOR_ATTACHMENT0 8
#define GL_TEXTURE_2D 9
#define GL_FRAMEBUFFER_COMPLETE 10
#define GL_RGBA 11
#define GL_UNSIGNED_BYTE 12
struct nvn_texture {unsigned live,name,draws;uint64_t id;struct {unsigned width,height;} b;};
static struct nvn_texture nvn_textures[4]={{1,101,1,7,{1280,720}},{1,102,42,8,{1920,1080}},{1,103,0,9,{1280,720}},{0,104,1,10,{1280,720}}};
static unsigned nvn_textures_high=4;
static struct {unsigned frames;} nvn_present;
static unsigned nvn_low_render_width(const struct nvn_texture *t){return t->b.width;}
static unsigned nvn_low_render_height(const struct nvn_texture *t){return t->b.height;}
static GLint read_fbo=17,draw_fbo=17,read_buffer=23,pack=4;
static unsigned reads,finishes;
static void glGetIntegerv(unsigned k,GLint *p){*p=k==GL_READ_FRAMEBUFFER_BINDING?read_fbo:k==GL_DRAW_FRAMEBUFFER_BINDING?draw_fbo:k==GL_READ_BUFFER?read_buffer:pack;}
static void glBindFramebuffer(unsigned k,GLuint n){if(k==GL_FRAMEBUFFER||k==GL_READ_FRAMEBUFFER)read_fbo=n;if(k==GL_FRAMEBUFFER||k==GL_DRAW_FRAMEBUFFER)draw_fbo=n;}
static void glGenFramebuffers(int n,GLuint *p){assert(n==1);*p=12345;}
static void glDeleteFramebuffers(int n,const GLuint *p){assert(n==1&&*p==12345&&read_fbo!=12345&&draw_fbo!=12345);}

static void glFramebufferTexture2D(unsigned a,unsigned b,unsigned c,GLuint t,int level){assert(a==GL_FRAMEBUFFER&&b==GL_COLOR_ATTACHMENT0&&c==GL_TEXTURE_2D&&(t==101||t==102)&&level==0);}
static unsigned glCheckFramebufferStatus(unsigned k){assert(k==GL_FRAMEBUFFER);return GL_FRAMEBUFFER_COMPLETE;}
static void glFinish(void){finishes++;}
static void glReadPixels(int x,int y,int w,int h,unsigned f,unsigned type,void *p){assert(x>=0&&y>=0&&w==1&&h==1&&f==GL_RGBA&&type==GL_UNSIGNED_BYTE);reads++;memset(p,127,4);}
static void step(unsigned frame){nvn_present.frames=frame;
BLOCK
assert(read_fbo==17&&draw_fbo==17&&read_buffer==23&&pack==4);
}
int main(int argc,char **argv){
 assert(argc==2);setenv("WOL_TARGET_PROBE",argv[1],1);
 step(0);assert(reads==0);step(128);step(640);step(1152);step(1664);
 assert(reads==(!strcmp(argv[1],"1")?30U:0U));assert(finishes==(!strcmp(argv[1],"1")?3U:0U));
 return 0;
}
'''.replace('BLOCK',block)
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'probe.c').write_text(code)
            subprocess.run(['cc','-std=gnu11','-O2','-Wall','-Wextra','-Werror',str(p/'probe.c'),'-o',str(p/'probe')],check=True)
            for flag in ('0','1'):
                result=subprocess.run([str(p/'probe'),flag],capture_output=True,text=True,check=True)
                self.assertEqual(result.stdout.count('WOL_TARGET_SAMPLE'),6 if flag=='1' else 0)


if __name__=='__main__':
    unittest.main()

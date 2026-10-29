"""Release-visible compositor state probe: opt-in, bounded, no GL mutation."""
from pathlib import Path
import os
import subprocess
import tempfile
import unittest


class ComposeTraceTests(unittest.TestCase):
    def test_real_probe_is_default_off_bounded_and_does_not_mutate_gl(self):
        patch=(Path(__file__).resolve().parents[1]/'runtime/wol-adapter.patch').read_text()
        added='\n'.join(l[1:] for l in patch.splitlines() if l.startswith('+') and not l.startswith('+++'))
        begin='/* WOL_COMPOSE_TRACE_BEGIN */';end='/* WOL_COMPOSE_TRACE_END */'
        self.assertTrue(begin in added and end in added,'missing compositor-state probe')
        block=added.split(begin,1)[1].split(end,1)[0]
        for forbidden in ('glBind','glDraw','glReadPixels','glGetError','glUniform','glFinish','nvn_gpu_pointer'):
            self.assertNotIn(forbidden,block)
        fixture=r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <inttypes.h>
typedef int GLint;
#define GL_TEXTURE_BINDING_2D 1
static void glGetIntegerv(int key,int *out){(void)key;*out=7;}
struct texture {unsigned live,name;uint64_t id;struct {unsigned width,height;} b;};
static struct texture nvn_textures[1]={{1,7,69,{1280,720}}};
static unsigned nvn_textures_high=1;
static struct {unsigned last_frame;} nvn_replay;
static struct {struct texture *target;unsigned attrib[3];uint64_t texture_handles[2][1];} nvn_render={&nvn_textures[0],{11,22,33},{{0},{1}}};
static struct {const char *name;} wol_cat_bindings[25];
static struct {int f,v;} linked={20,19};
static struct {const uint16_t *indices;} geometry;
static void probe(void) {
    void *unused=NULL;(void)unused;(void)geometry;
    struct {int f,v;} *bad=NULL;(void)bad;
    __typeof__(&linked) wol_cat_cur=&linked;
    float words[96]={0},fwords[96]={1,1,1,1};
    unsigned char vertex[64];for(unsigned i=0;i<sizeof vertex;i++)vertex[i]=(unsigned char)(i%251+1);
    const unsigned char *base=vertex;
    uint64_t stride=20,count=6,first=0;
    (void)count;(void)first;
'''+block+r'''
}
int main(void){
    wol_cat_bindings[19].name="vertex";wol_cat_bindings[20].name="fragment";
    for(unsigned f=0;f<8000;f+=128){nvn_replay.last_frame=f;probe();probe();}
    return 0;
}
'''
        # The sprite and WANTED stages must not be silently excluded by the old
        # f<=24 predicate. Same pair/target with a different batch is new evidence.
        fixture=fixture.replace('wol_cat_bindings[25]', 'wol_cat_bindings[35]')
        fixture=fixture.replace('vertex[64]', 'vertex[512]')
        coverage=fixture.replace('int main(void){', 'int old_main(void){')+r'''
int main(void){
    static const uint16_t indices[6]={3,2,1,3,1,0};geometry.indices=indices;
    for(int f=20;f<=34;f+=2) {
        wol_cat_bindings[f-1].name="vertex";wol_cat_bindings[f].name="fragment";
        linked.v=f-1;linked.f=f;nvn_replay.last_frame=128;probe();probe();
    }
    return 0;
}
'''
        with tempfile.TemporaryDirectory() as d:
            c=Path(d)/'probe.c';binary=Path(d)/'probe';c.write_text(fixture)
            subprocess.run(['cc','-std=gnu11','-Wall','-Wextra','-Werror',str(c),'-o',str(binary)],check=True,capture_output=True)
            for value,expected in [(None,0),('0',0),('yes',0),('1',4)]:
                with self.subTest(env=value):
                    env=dict(os.environ);env.pop('WOL_COMPOSE_TRACE',None)
                    if value is not None:env['WOL_COMPOSE_TRACE']=value
                    lines=subprocess.run([str(binary)],env=env,check=True,text=True,capture_output=True).stdout.splitlines()
                    self.assertEqual(len(lines),expected)
                    for line in lines:
                        self.assertTrue(line.startswith('WOL_COMPOSE_TRACE '))
                        self.assertIn('sample=69/1280x720',line)
                        self.assertIn('c3f=1,1,1,1',line)
            c.write_text(coverage)
            subprocess.run(['cc','-std=gnu11','-Wall','-Wextra','-Werror',str(c),'-o',str(binary)],check=True,capture_output=True)
            env=dict(os.environ,WOL_COMPOSE_TRACE='1')
            lines=subprocess.run([str(binary)],env=env,check=True,text=True,capture_output=True).stdout.splitlines()
            self.assertEqual(len(lines),8,'sprite/WANTED/farm mesh passes were excluded from the probe')
            for line in lines:
                raw=bytes.fromhex(line.split(' raw0=',1)[1])
                self.assertEqual([raw[i*20] for i in range(6)],[61,41,21,61,21,1],
                                 'probe must inspect referenced vertices, not unused buffer gaps')


if __name__=='__main__':unittest.main()

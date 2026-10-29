"""Only new update vertices may opt into the existing NVN clip wrapper."""
from pathlib import Path
import os
import subprocess
import tempfile
import unittest


class UpdateClipTests(unittest.TestCase):
    def test_existing_clip_wrapper_is_selected_only_for_opted_in_update_vertices(self):
        patch=(Path(__file__).resolve().parents[1]/'runtime/wol-adapter.patch').read_text()
        added='\n'.join(l[1:] for l in patch.splitlines() if l.startswith('+') and not l.startswith('+++'))
        begin='/* WOL_UPDATE_CLIP_SOURCE_BEGIN */';end='/* WOL_UPDATE_CLIP_SOURCE_END */'
        self.assertTrue(begin in added and end in added,'missing NVN clip integration')
        block=added.split(begin,1)[1].split(end,1)[0]
        self.assertIn('lk->clip=glGetUniformLocation(pr,"nvnClipControl")',added)
        self.assertIn('glUniform2f(wol_cat_cur->clip,nvn_device.window_origin?-1.0f:1.0f,(GLfloat)nvn_device.depth_mode)',added)
        self.assertNotIn('u_wol_rt_yflip',added)
        fixture=r'''
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static unsigned long nvn_caller;
static void stop(const char *name,unsigned long pc,unsigned value,int code){(void)pc;(void)value;puts(name);exit(code);}
/* Dependency stub: helper itself is unchanged; exercise selection and ownership. */
static char *nvn_clip_vertex_source(const char *source){(void)source;char *p=malloc(8);memcpy(p,"wrapped",8);return p;}
static int select_source(int v){
    unsigned fullscreen=0;const char *src="original";
'''+block+r'''
    int changed=!strcmp(src,"wrapped");free(update_clip);return changed;
}
int main(void){int a=select_source(0),b=select_source(19),c=select_source(25);printf("%d %d %d\n",a,b,c);return 0;}
'''
        with tempfile.TemporaryDirectory() as d:
            c=Path(d)/'clip.c';binary=Path(d)/'clip';c.write_text(fixture)
            subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror',str(c),'-o',str(binary)],check=True,capture_output=True)
            for value,expected in [(None,'0 0 0'),('0','0 0 0'),('1','0 1 1')]:
                env=dict(os.environ);env.pop('WOL_UPDATE_CLIP_CONTROL',None)
                if value is not None:env['WOL_UPDATE_CLIP_CONTROL']=value
                out=subprocess.run([str(binary)],check=True,capture_output=True,text=True,env=env)
                self.assertEqual(out.stdout.strip(),expected)


if __name__=='__main__':unittest.main()

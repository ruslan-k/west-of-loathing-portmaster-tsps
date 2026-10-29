"""Update c4 shaders use NVN uniform slot 1, even with live c3/slot 0."""
from pathlib import Path
import re
import subprocess
import tempfile
import unittest


class VertexBankTests(unittest.TestCase):
    def test_real_caller_does_not_take_stale_c3_for_an_observed_c4_shader(self):
        patch=(Path(__file__).resolve().parents[1]/'runtime/wol-adapter.patch').read_text()
        added='\n'.join(l[1:] for l in patch.splitlines() if l.startswith('+') and not l.startswith('+++'))
        bindings=re.findall(r'\{\s*\d+,0x(?:848|880),([01]),[01],"([^"]+)"',added)
        self.assertGreaterEqual(len(bindings),35,'missing farm mesh shader identities')
        for index,name in [(19,'a4245675'),(21,'fb2f4788'),(23,'6a930d0e'),(27,'6a930d0e-ui'),(29,'e56d57b0'),(31,'6054acba-mesh'),(33,'a4245675-mesh')]:
            self.assertEqual(bindings[index],('0','update-'+name+'-diagnostic'))
        begin='/* WOL_VERTEX_BANK_BEGIN */';end='/* WOL_VERTEX_BANK_END */'
        self.assertTrue(begin in added and end in added,'missing shader-specific vertex bank selection')
        block=added.split(begin,1)[1].split(end,1)[0]
        fixture=r'''
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <assert.h>
struct nvn_range {uint64_t address,size;};
static struct {struct nvn_range uniform[2][16];} nvn_render;
static uint64_t nvn_caller;
static void stop(const char *why,uint64_t caller,uint64_t detail,int code){
    (void)caller;(void)detail;puts(why);exit(code);
}
static unsigned select_bank(int v,uint64_t *address) {
    struct {int v;} linked={v},*wol_cat_cur=&linked;
'''+block+r'''
    *address=c3r.address;return bank;
}
int main(int argc,char **argv){
    (void)argv;
    nvn_render.uniform[0][0]=(struct nvn_range){0x1000,176};
    nvn_render.uniform[0][1]=(struct nvn_range){0x2000,176};
    uint64_t address=0;
    const int c4[]={19,21,23,27,29,31,33};
    for(unsigned i=0;i<sizeof(c4)/sizeof(c4[0]);i++){assert(select_bank(c4[i],&address)==1);assert(address==0x2000);}
    assert(select_bank(25,&address)==0&&address==0x1000);
    assert(select_bank(0,&address)==0&&address==0x1000);
    nvn_render.uniform[0][0]=(struct nvn_range){0,0};
    assert(select_bank(0,&address)==1&&address==0x2000); /* legacy behavior unchanged */
    if(argc>1){
        nvn_render.uniform[0][0]=(struct nvn_range){0x1000,176};
        if(argv[1][0]=='b'){
            nvn_render.uniform[0][1]=(struct nvn_range){0x2000,127};
            select_bank(31,&address);return 99;
        }
        if(argv[1][0]=='m'){
            nvn_render.uniform[0][1]=(struct nvn_range){0x2000,143};
            select_bank(33,&address);return 99;
        }
        nvn_render.uniform[0][1]=(struct nvn_range){0x2000,128};
        select_bank(19,&address);return 99; /* must refuse, never fall back to slot 0 */
    }
    puts("BANK_SELECTION_OK");return 0;
}
'''
        with tempfile.TemporaryDirectory() as d:
            c=Path(d)/'bank.c';binary=Path(d)/'bank';c.write_text(fixture)
            subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror',str(c),'-o',str(binary)],check=True,capture_output=True)
            out=subprocess.run([str(binary)],check=True,capture_output=True,text=True)
            self.assertEqual(out.stdout.strip(),'BANK_SELECTION_OK')
            bad=subprocess.run([str(binary),'short-required-bank'],capture_output=True,text=True)
            self.assertEqual(bad.returncode,24)
            self.assertEqual(bad.stdout.strip(),'WOL_UPDATE_VERTEX_BANK')
            mesh_bad=subprocess.run([str(binary),'body-short-required-bank'],capture_output=True,text=True)
            self.assertEqual(mesh_bad.returncode,24)
            self.assertEqual(mesh_bad.stdout.strip(),'WOL_UPDATE_VERTEX_BANK')
            farm_bad=subprocess.run([str(binary),'mesh-short-required-bank'],capture_output=True,text=True)
            self.assertEqual(farm_bad.returncode,24)
            self.assertEqual(farm_bad.stdout.strip(),'WOL_UPDATE_VERTEX_BANK')


if __name__=='__main__':unittest.main()

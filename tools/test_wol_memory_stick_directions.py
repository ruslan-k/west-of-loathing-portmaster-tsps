"""Npad stick direction bits must accompany the existing analog coordinates."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]

class StickDirectionTests(unittest.TestCase):
    def test_published_npad_samples_include_both_stick_direction_masks(self):
        patch=(ROOT/'runtime/wol-adapter.patch').read_text()
        added='\n'.join(l[1:] for l in patch.splitlines() if l.startswith('+') and not l.startswith('+++'))
        begin='/* WOL_NPAD_STICK_DIRECTIONS_BEGIN */';end='/* WOL_NPAD_STICK_DIRECTIONS_END */'
        self.assertTrue(begin in added and end in added,'missing Npad stick direction synthesis')
        self.assertTrue('hid_sample_stick_directions(&sample);' in added,'synthesis must feed the shared Npad publisher')
        helper=added.split(begin,1)[1].split(end,1)[0]
        code=r'''
#include <assert.h>
#include <stdint.h>
#include <limits.h>
struct hid_sample {uint64_t number,buttons;int32_t lx,ly,rx,ry;uint32_t attributes,reserved;};
_Static_assert(sizeof(struct hid_sample)==0x28,"guest Npad ABI unchanged");
'''+helper+r'''
int main(void){
    const uint64_t keep=UINT64_C(0x10000000000)|UINT64_C(0xa441);
    struct hid_sample sample={.number=19,.buttons=keep,.attributes=1,.reserved=123};
    hid_sample_stick_directions(&sample);assert(sample.buttons==keep);
    for(unsigned axis=0;axis<4;axis++)for(int sign=-1;sign<=1;sign+=2){
        for(unsigned i=0;i<3;i++){
            int32_t magnitude=i==0?16383:i==1?16384:32767;
            struct hid_sample s={.number=19,.buttons=keep,.attributes=1,.reserved=123};
            int32_t *values[]={&s.lx,&s.ly,&s.rx,&s.ry};*values[axis]=sign*magnitude;
            /* Layout is L-left/up/right/down then R-left/up/right/down. */
            const unsigned bits[4][2]={{16,18},{19,17},{20,22},{23,21}};
            unsigned bit=bits[axis][sign>0];
            hid_sample_stick_directions(&s);
            assert(s.buttons==(keep|(i?UINT64_C(1)<<bit:0)));
            assert(*values[axis]==sign*magnitude&&s.number==19&&s.attributes==1&&s.reserved==123);
        }
    }
    sample=(struct hid_sample){.buttons=keep,.lx=INT32_MIN,.ly=INT32_MAX,.rx=INT32_MAX,.ry=INT32_MIN};
    hid_sample_stick_directions(&sample);
    assert(sample.buttons==(keep|(UINT64_C(1)<<16)|(UINT64_C(1)<<17)|(UINT64_C(1)<<22)|(UINT64_C(1)<<23)));
    sample=(struct hid_sample){.buttons=keep};hid_sample_stick_directions(&sample);assert(sample.buttons==keep);
    return 0;
}
'''
        with tempfile.TemporaryDirectory() as td:
            source=Path(td)/'stick.c';binary=Path(td)/'stick';source.write_text(code)
            p=subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror',str(source),'-o',str(binary)],capture_output=True,text=True)
            self.assertEqual(p.returncode,0,p.stderr)
            p=subprocess.run([str(binary)],capture_output=True,text=True)
            self.assertEqual(p.returncode,0,p.stdout+p.stderr)

if __name__=='__main__':unittest.main()

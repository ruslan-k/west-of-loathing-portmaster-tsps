#!/usr/bin/env python3
"""The read-only guest-frame walker refuses malformed/unreadable chains."""
import subprocess
import tempfile
import unittest
from pathlib import Path
from test_wol_memory_handheld import added_header


class RtOriginContract(unittest.TestCase):
    def test_bounded_aligned_own_stack_only_and_no_mutations(self):
        h = added_header('wol_rt_origin.h')
        c = r'''
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include <assert.h>
static uint64_t data[64];static unsigned reads;
static int read_pair(void *opaque,uint64_t address,uint64_t pair[2]) {
    assert(opaque==data);reads++;
    if(address<0x1000 || address>0x11f0)return 0;
    memcpy(pair,(uint8_t *)data+address-0x1000,16);return 1;
}
''' + h + r'''
int main(void) {
    uint64_t out[8]={0};data[0]=0x1020;data[1]=0x100;data[4]=0x1040;data[5]=0x200;
    data[8]=0;data[9]=0x300;
    assert(wol_rt_origin_frames(0x1000,0x1000,out,8,read_pair,data)==3);
    assert(out[0]==0x100&&out[1]==0x200&&out[2]==0x300);
    assert(wol_rt_origin_frames(0x1000,0x1000,out,1,read_pair,data)==1);
    reads=0;assert(!wol_rt_origin_frames(0x1001,0x1000,out,8,read_pair,data));assert(!reads);
    assert(!wol_rt_origin_frames(0x1000,0x1010,out,8,read_pair,data));assert(!reads);
    assert(!wol_rt_origin_frames(0x101000,0x1000,out,8,read_pair,data));assert(!reads);
    data[0]=0x1000;assert(wol_rt_origin_frames(0x1000,0x1000,out,8,read_pair,data)==1);
    data[0]=0x1020;data[4]=0x1000;assert(wol_rt_origin_frames(0x1000,0x1000,out,8,read_pair,data)==2);
    assert(!wol_rt_origin_frames(0x1200,0x1000,out,8,read_pair,data));
    assert(data[1]==0x100&&data[5]==0x200&&data[9]==0x300);
    assert(!wol_rt_origin_frames(0x1000,0x1000,NULL,8,read_pair,data));
}
'''
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            (p/'t.c').write_text(c)
            subprocess.run(['cc','-O2','-std=gnu11','-Wall','-Wextra','-Werror',str(p/'t.c'),'-o',str(p/'t')],check=True)
            subprocess.run([str(p/'t')],check=True)


if __name__ == '__main__':
    unittest.main()

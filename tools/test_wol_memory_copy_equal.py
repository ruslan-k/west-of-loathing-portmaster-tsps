#!/usr/bin/env python3
"""Compiled data-free exact destination-copy snapshot diagnostic contract."""
import subprocess
import tempfile
import unittest
from pathlib import Path
from test_wol_memory_handheld import added_header


class CopyEqualityContract(unittest.TestCase):
    def test_exact_bytes_identity_epochs_and_bounded_storage(self):
        header=added_header('wol_copy_equal.h')
        code=r'''
#include <stdint.h>
#include <stddef.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
'''+header+r'''
int main(void) {
    struct wol_copy_equal_state s={0};
    struct wol_copy_equal_key k={.object=1,.id=7,.pool=0x1000,.address=0x2000,.bytes=8,.name=3,.context=4};
    uint8_t a[8]={0},b[8]={0};
    assert(wol_copy_equal_observe(&s,&k,a)==0);
    assert(wol_copy_equal_observe(&s,&k,b)==1);
    b[7]=1;assert(wol_copy_equal_observe(&s,&k,b)==2);
    assert(wol_copy_equal_observe(&s,&k,b)==1);
    k.id++;assert(wol_copy_equal_observe(&s,&k,b)==0);
    k.context++;assert(wol_copy_equal_observe(&s,&k,b)==0);
    k.name++;assert(wol_copy_equal_observe(&s,&k,b)==0);
    k.address++;assert(wol_copy_equal_observe(&s,&k,b)==0);
    k.bytes=0;assert(wol_copy_equal_observe(&s,&k,b)==3);
    k.bytes=WOL_COPY_EQUAL_LIMIT+1;assert(wol_copy_equal_observe(&s,&k,b)==3);
    free(s.snapshot);
}
'''
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'test.c').write_text(code)
            subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror',str(p/'test.c'),'-o',str(p/'test')],check=True)
            subprocess.run([str(p/'test')],check=True)


if __name__=='__main__':unittest.main()

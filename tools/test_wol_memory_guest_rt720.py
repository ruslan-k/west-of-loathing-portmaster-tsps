#!/usr/bin/env python3
"""Compiled startup guest-dimension patch: exact identity and atomic refusal.

Fixture words are independently recorded from the pinned original AArch64
image. They are not copied from the implementation's patch table.
"""
import subprocess
import tempfile
import unittest
from pathlib import Path
from test_wol_memory_handheld import added_header


class Guest720Contract(unittest.TestCase):
    def test_guest_dimensions_and_builders_agree_or_leave_every_byte_untouched(self):
        header = added_header('wol_guest_rt720.h')
        code = r'''
#include <stdint.h>
#include <stddef.h>
#include <stdlib.h>
#include <string.h>
#include <assert.h>
''' + header + r'''
static const struct {uint32_t off,old_word,new_word;} fixture[] = {
    {0xaef090,0x52808709U,0x52805a09U},
    {0xaef094,0x32190fe8U,0x5280a008U},
    {0xaef0ac,0x32190fe8U,0x5280a008U},
    {0xaef0b4,0x52808708U,0x52805a08U},
    {0xaef47c,0x52808714U,0x52805a14U},
    {0xaef480,0x32190fe1U,0x5280a001U},
    {0xaef520,0x32190fe1U,0x5280a001U},
    {0xaef6b0,0x32190fe1U,0x5280a001U},
    {0xaef6b4,0x52808702U,0x52805a02U},
    {0xaef7e4,0x52808703U,0x52805a03U},
    {0xaef7e8,0x32190fe2U,0x5280a002U},
};
int main(void) {
    const char *sha="df8a2524a65ec784f5781908be3734fa7c448f16c4c1029ee5b0fd4b63a0de84";
    size_t n=0xb00000;
    uint8_t *bytes=malloc(n),*original=malloc(n),*expected=malloc(n);
    assert(bytes&&original&&expected);
    memset(original,0xa5,n);
    for(unsigned i=0;i<11;i++)memcpy(original+fixture[i].off,&fixture[i].old_word,4);
    memcpy(expected,original,n);
    for(unsigned i=0;i<11;i++)memcpy(expected+fixture[i].off,&fixture[i].new_word,4);
    memcpy(bytes,original,n);
    assert(!wol_guest_rt720_apply(bytes,n,"wrong"));assert(!memcmp(original,bytes,n));
    assert(!wol_guest_rt720_apply(NULL,n,sha));
    assert(!wol_guest_rt720_apply(bytes,n,NULL));
    assert(!wol_guest_rt720_apply(bytes,0xaef7eb,sha));assert(!memcmp(original,bytes,n));
    for(unsigned i=0;i<11;i++) {
        memcpy(bytes,original,n);bytes[fixture[i].off]^=1;
        memcpy(expected,bytes,n);
        assert(!wol_guest_rt720_apply(bytes,n,sha));assert(!memcmp(expected,bytes,n));
    }
    memcpy(bytes,original,n);memcpy(expected,original,n);
    for(unsigned i=0;i<11;i++)memcpy(expected+fixture[i].off,&fixture[i].new_word,4);
    assert(wol_guest_rt720_apply(bytes,n,sha));assert(!memcmp(expected,bytes,n));
    assert(!wol_guest_rt720_apply(bytes,n,sha));assert(!memcmp(expected,bytes,n));
    free(expected);free(original);free(bytes);
}
'''
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            (p/'test.c').write_text(code)
            subprocess.run(['cc', '-std=gnu11', '-O2', '-Wall', '-Wextra', '-Werror',
                            str(p/'test.c'), '-o', str(p/'test')], check=True)
            subprocess.run([str(p/'test')], check=True)


if __name__ == '__main__':
    unittest.main()

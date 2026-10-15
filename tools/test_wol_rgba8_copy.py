#!/usr/bin/env python3
"""Compile the real exact-copy helper; check bytes, eligibility and refresh fallback."""
from pathlib import Path
import os, subprocess, sys, tempfile
n=Path(sys.argv[1]);h=(n/'nvn_texture_formats.h').read_text();t=(n/'nvn_textures.h').read_text()
assert 'nvn_texture_copy_rgba8' in h, 'missing exact identity-RGBA8 bulk-copy helper'
assert 'getenv("WOL_RGBA8_COPY")' in t, 'missing reversible refresh-only A/B switch'
refresh=t.split('static void zero_texture_refresh(',1)[1].split('#include "zero_texture_writes.h"',1)[0]
assert 'stride==row' in refresh and 'type==GL_UNSIGNED_BYTE' in refresh and 'nvn_texture_copy_rgba8' in refresh
for guard in ('ZERO_TEXTURE_CPU_GPU_COHERENCE_REQUIRED','ZERO_TEXTURE_REFRESH_RANGE','ZERO_TEXTURE_REFRESH_GL','nvn_texture_decode_upload','glTexSubImage2D','free(pixels)'):
    assert guard in refresh, 'copy path must retain '+guard
code=r'''
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "nvn_texture_formats.h"
int main(void) {
    uint8_t src[4*257],old[4*257],fast[4*257];
    for(size_t p=0;p<257;p++)for(unsigned c=0;c<4;c++)src[p*4+c]=(uint8_t)(p*(c*2+1)+c*71);
    unsigned accepted=0;
    for(unsigned f=0;f<2;f++)for(unsigned word=0;word<1296;word++) {
        unsigned z=word;uint32_t sw[4];for(unsigned c=0;c<4;c++){sw[c]=z%6;z/=6;}
        unsigned format=f?0x9a:0x25;
        memset(fast,0xa5,sizeof(fast));
        assert(nvn_texture_decode_rgba(format,sw,old,src,257));
        unsigned want=format==0x25 && sw[0]==2 && sw[1]==3 && sw[2]==4 && sw[3]==5;
        assert(nvn_texture_copy_rgba8(format,sw,fast,src,257)==want);
        if(want){assert(!memcmp(old,fast,sizeof(old)));accepted++;}
        else for(size_t i=0;i<sizeof(fast);i++)assert(fast[i]==0xa5);
    }
    assert(accepted==1);
    uint32_t id[4]={2,3,4,5},bad[4]={2,3,4,6};
    assert(!nvn_texture_copy_rgba8(0x25,bad,fast,src,1));
    for(unsigned f=0;f<256;f++)if(f!=0x25)assert(!nvn_texture_copy_rgba8(f,id,fast,src,1));
    size_t sizes[]={0,1,3,31,1280,1280*720};
    for(unsigned j=0;j<sizeof(sizes)/sizeof(sizes[0]);j++) {
        size_t size=sizes[j]*4;uint8_t *a=malloc(size+32),*b=malloc(size+32),*c=malloc(size+32);
        assert(a&&b&&c);memset(b,0xa5,size+32);memset(c,0xa5,size+32);
        for(size_t i=0;i<size+32;i++)a[i]=(uint8_t)(i*13+(i>>7));
        assert(nvn_texture_decode_rgba(0x25,id,c+7,a+3,sizes[j]));
        assert(nvn_texture_copy_rgba8(0x25,id,b+7,a+3,sizes[j]));
        assert(!memcmp(b,c,size+32));free(a);free(b);free(c);
    }
    assert(!nvn_texture_copy_rgba8(0x25,id,fast,src,SIZE_MAX/4+1));
    uint8_t overlap[32],expected[32];for(unsigned i=0;i<32;i++)overlap[i]=expected[i]=(uint8_t)i;
    memmove(expected+3,expected,16);assert(nvn_texture_copy_rgba8(0x25,id,overlap+3,overlap,4));assert(!memcmp(overlap,expected,32));
    puts("PASS RGBA8 exact copy: all 1296 swizzles x two formats, byte patterns, unaligned/full-frame/zero/overflow/overlap, fallback untouched");
    return 0;
}
'''
with tempfile.TemporaryDirectory(prefix='wol-rgba8-copy-',dir=os.environ.get('TMPDIR')) as d:
    p=Path(d);(p/'test.c').write_text(code)
    subprocess.run(['cc','-O2','-std=c11','-Wall','-Wextra','-Werror','-I',str(n),str(p/'test.c'),'-o',str(p/'test')],check=True)
    subprocess.run([str(p/'test')],check=True)

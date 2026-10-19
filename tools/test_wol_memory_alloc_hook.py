#!/usr/bin/env python3
"""Exercise the actual overlay's opt-in allocator instruction hook, without game data."""
from pathlib import Path
import os
import re
import shutil
import subprocess
import tempfile
import unittest


class AllocHookTests(unittest.TestCase):
    def test_disabled_and_alloc_free_realloc_preserve_guest_instruction_semantics(self):
        patch=(Path(__file__).resolve().parents[1]/'runtime/wol-adapter.patch').read_text()
        part=patch.split('--- a/native/graphics_trace.h\n',1)[1].split('\n--- ',1)[0]
        added='\n'.join(l[1:] for l in part.splitlines() if l.startswith('+') and not l.startswith('+++'))
        code=added[added.index('/* WOL_ALLOC_TRACE=1:'):]
        prefix=r'''
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <assert.h>
#define MAX_THREADS 4
#define LC2_SDK_BASE 0xa78f000ULL
#define LC2_SDK_SHA256 "3c5fc6933f619271feb42f62519e9f9043d06f3ee76746552b6b4cfe9094537e"
static unsigned guest_thread_index;
typedef struct {struct {uint64_t regs[31],sp,pc;} uc_mcontext;} ucontext_t;
struct line {unsigned unused;};
static void text(struct line *l,const char *s){(void)l;(void)s;}
static void hex(struct line *l,uint64_t v){(void)l;(void)v;}
static void location(struct line *l,uint64_t v){(void)l;(void)v;}
static void emit(struct line *l){(void)l;}
static int accessible(uint64_t a,uint64_t n,int p){(void)n;(void)p;return a!=0;}
#define PROT_READ 1
#define PROT_WRITE 2
static void stop(const char *s,uint64_t p,uint64_t v,unsigned n){(void)p;(void)v;(void)n;fprintf(stderr,"%s\n",s);abort();}
'''
        main=r'''
int main(void){
    uint64_t stack[64]={0};ucontext_t c={0};
    c.uc_mcontext.sp=(uintptr_t)(stack+48);c.uc_mcontext.regs[30]=0x1234;
    uint64_t original=c.uc_mcontext.sp;
    unsetenv("WOL_ALLOC_TRACE");wol_alloc_configure();
    assert(!wol_alloc_handle(LC2_SDK_BASE+0x830a0,0xd10103ff,&c));
    assert(c.uc_mcontext.sp==original);
    setenv("WOL_ALLOC_TRACE","1",1);wol_alloc_configure();
    c.uc_mcontext.pc=LC2_SDK_BASE+0x830a0;c.uc_mcontext.regs[0]=0x8000;c.uc_mcontext.regs[1]=2097152;
    assert(wol_alloc_handle(c.uc_mcontext.pc,0xd10103ff,&c));
    assert(c.uc_mcontext.sp==original-64 && c.uc_mcontext.regs[0]==0x8000);
    c.uc_mcontext.sp=original;c.uc_mcontext.pc=LC2_SDK_BASE+0x8318c;c.uc_mcontext.regs[0]=0x10000000;
    assert(wol_alloc_handle(c.uc_mcontext.pc,0xd65f03c0,&c));
    assert(c.uc_mcontext.pc==0x1234 && c.uc_mcontext.regs[0]==0x10000000);
    assert(wol_alloc_live[0].ptr==0x10000000 && wol_alloc_live[0].size==2097152);
    /* Failed realloc must keep the old live allocation. */
    c.uc_mcontext.pc=LC2_SDK_BASE+0x831f8;c.uc_mcontext.regs[0]=0x8000;c.uc_mcontext.regs[1]=0x10000000;c.uc_mcontext.regs[2]=4194304;
    wol_alloc_handle(c.uc_mcontext.pc,0xd10103ff,&c);c.uc_mcontext.sp=original;c.uc_mcontext.pc=LC2_SDK_BASE+0x83320;c.uc_mcontext.regs[0]=0;
    wol_alloc_handle(c.uc_mcontext.pc,0xd65f03c0,&c);assert(wol_alloc_live[0].ptr==0x10000000);
    c.uc_mcontext.pc=LC2_SDK_BASE+0x83198;c.uc_mcontext.regs[1]=0x10000000;c.uc_mcontext.regs[20]=77;c.uc_mcontext.regs[19]=88;
    assert(wol_alloc_handle(c.uc_mcontext.pc,0xa9be4ff4,&c));
    assert(c.uc_mcontext.sp==original-32 && c.uc_mcontext.pc==LC2_SDK_BASE+0x8319c);
    uint64_t *saved=(uint64_t *)(uintptr_t)c.uc_mcontext.sp;assert(saved[0]==77 && saved[1]==88);
    /* Lowered threshold: WOL_ALLOC_MIN=262144 tracks a 300000-byte request and skips 200000. */
    c.uc_mcontext.sp=original;
    setenv("WOL_ALLOC_MIN","262144",1);wol_alloc_configure();
    c.uc_mcontext.pc=LC2_SDK_BASE+0x830a0;c.uc_mcontext.regs[0]=0x8000;c.uc_mcontext.regs[1]=200000;
    assert(wol_alloc_handle(c.uc_mcontext.pc,0xd10103ff,&c));
    c.uc_mcontext.sp=original;c.uc_mcontext.pc=LC2_SDK_BASE+0x8318c;c.uc_mcontext.regs[0]=0x20000000;
    assert(wol_alloc_handle(c.uc_mcontext.pc,0xd65f03c0,&c));
    assert(!wol_alloc_live[0].ptr);
    c.uc_mcontext.pc=LC2_SDK_BASE+0x830a0;c.uc_mcontext.regs[0]=0x8000;c.uc_mcontext.regs[1]=300000;
    assert(wol_alloc_handle(c.uc_mcontext.pc,0xd10103ff,&c));
    c.uc_mcontext.sp=original;c.uc_mcontext.pc=LC2_SDK_BASE+0x8318c;c.uc_mcontext.regs[0]=0x30000000;
    assert(wol_alloc_handle(c.uc_mcontext.pc,0xd65f03c0,&c));
    assert(wol_alloc_live[0].ptr==0x30000000 && wol_alloc_live[0].size==300000);
    c.uc_mcontext.pc=LC2_SDK_BASE+0x83198;c.uc_mcontext.regs[1]=0x30000000;c.uc_mcontext.regs[20]=91;c.uc_mcontext.regs[19]=92;
    assert(wol_alloc_handle(c.uc_mcontext.pc,0xa9be4ff4,&c));
    unsetenv("WOL_ALLOC_MIN");wol_alloc_configure();
    assert(!wol_alloc_live[0].ptr);assert(wol_alloc_logged==4);assert(!wol_alloc_depth[0]);
    puts("ALLOC_HOOK_SEMANTICS_OK");return 0;
}
'''
        with tempfile.TemporaryDirectory() as td:
            p=Path(td);(p/'probe.c').write_text(prefix+code+main)
            cc=shutil.which('cc') or shutil.which('gcc')
            self.assertIsNotNone(cc)
            subprocess.run([cc,'-std=gnu11','-O2','-Wall','-Wextra','-Werror',str(p/'probe.c'),'-o',str(p/'probe')],check=True)
            out=subprocess.run([str(p/'probe')],capture_output=True,text=True,check=True)
            self.assertIn('ALLOC_HOOK_SEMANTICS_OK',out.stdout)


if __name__=='__main__':
    unittest.main()

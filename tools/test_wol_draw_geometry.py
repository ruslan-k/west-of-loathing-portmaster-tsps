#!/usr/bin/env python3
"""Compile the actual WoL geometry decoder, not a Python reimplementation.
Synthetic fixtures exercise the real observed DrawElementsBaseVertex ABI.
Usage: python3 tools/test_wol_draw_geometry.py path/to/native/nvn_render.h
"""
import os
from pathlib import Path
import subprocess
import sys
import tempfile

source = Path(sys.argv[1]).read_text()
begin = "/* WOL_DRAW_GEOMETRY_BEGIN */"
end = "/* WOL_DRAW_GEOMETRY_END */"
assert begin in source and end in source, (
    "WoL hook has no opcode-aware geometry decoder: indexed draws are treated as arrays"
)
code = source.split(begin, 1)[1].split(end, 1)[0]
preamble = r'''
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <assert.h>
#include <setjmp.h>
#define PROT_READ 1
#define NI_nvnCommandBufferDrawArrays 10
#define NI_nvnCommandBufferDrawElements 11
#define NI_nvnCommandBufferDrawElementsBaseVertex 12
struct nvn_record {unsigned op; uint64_t args[5];};
static uint64_t nvn_caller;
static jmp_buf failure;
static const char *last_stop;
static void stop(const char *why,uint64_t pc,uint64_t detail,int status) {
    (void)pc;(void)detail;(void)status; last_stop=why;longjmp(failure,1);
}
static void *nvn_gpu_pointer(uint64_t p,uint64_t n,unsigned perm) {
    (void)n;(void)perm;return (void *)(uintptr_t)p;
}
static uint32_t read32(const uint8_t *p) {
    return p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);
}
static uint16_t *nvn_render_index_scratch(uint64_t n) {
    static uint16_t buf[128];assert(n<=128);return buf;
}
'''
cases = r'''
int main(void) {
    /* Synthetic quad fixture: triangles, uint16 indices, nonzero base vertex. */
    uint16_t quad[]={0,1,2,2,3,0};
    struct nvn_record r={NI_nvnCommandBufferDrawElementsBaseVertex,
        {4,1,6,(uint64_t)(uintptr_t)quad,4}};
    struct wol_draw_geometry g;
    assert(wol_decode_draw_geometry(&r,&g));
    assert(g.primitive==4 && g.base==4 && g.maximum==3 && g.count==6);
    assert(g.indices && !memcmp(g.indices,quad,sizeof quad));
    puts("PASS u16 indexed basevertex: type=1 is NOT first=1; 6 indices address 4 vertices");
    uint8_t small[]={5,7,6};
    r.op=NI_nvnCommandBufferDrawElements;r.args[1]=0;r.args[2]=3;r.args[3]=(uint64_t)(uintptr_t)small;
    assert(wol_decode_draw_geometry(&r,&g));
    assert(g.base==5 && g.maximum==2 && g.indices[0]==0 && g.indices[1]==2 && g.indices[2]==1);
    puts("PASS u8 rebase preserves order");
    uint32_t wide[]={70000,70002,70001};
    r.args[1]=2;r.args[3]=(uint64_t)(uintptr_t)wide;
    assert(wol_decode_draw_geometry(&r,&g));
    assert(g.base==70000 && g.maximum==2 && g.indices[0]==0 && g.indices[1]==2 && g.indices[2]==1);
    puts("PASS u32 rebased to u16 without truncation");
    r.op=NI_nvnCommandBufferDrawArrays;r.args[1]=9;r.args[2]=6;
    assert(wol_decode_draw_geometry(&r,&g));
    assert(g.base==9 && g.maximum==5 && g.count==6 && !g.indices);
    puts("PASS arrays honor first separately");
    r.args[2]=0;assert(!wol_decode_draw_geometry(&r,&g));
    puts("PASS empty draw");
    r.op=NI_nvnCommandBufferDrawElementsBaseVertex;r.args[1]=1;r.args[2]=6;
    r.args[3]=(uint64_t)(uintptr_t)quad;r.args[4]=(uint32_t)-1;
    if(!setjmp(failure)){wol_decode_draw_geometry(&r,&g);assert(!"negative vertex accepted");}
    assert(!strcmp(last_stop,"WOL_INDEX_NEGATIVE_VERTEX"));
    puts("PASS negative base refused");
    r.args[4]=0;r.args[1]=3;
    if(!setjmp(failure)){wol_decode_draw_geometry(&r,&g);assert(!"invalid index type accepted");}
    assert(!strcmp(last_stop,"WOL_INDEX_RANGE"));
    puts("PASS invalid index type refused");
    return 0;
}
'''
with tempfile.TemporaryDirectory(prefix="wol-geometry-", dir=os.environ.get("TMPDIR")) as tmp:
    c = Path(tmp) / "probe.c"
    c.write_text(preamble + code + cases)
    exe = Path(tmp) / "probe"
    subprocess.run(["cc", "-std=c11", "-Wall", "-Wextra", "-Werror", "-O1", str(c), "-o", str(exe)], check=True)
    subprocess.run([str(exe)], check=True)
hook = source.split("static void nvn_render_draw_inner",1)[1].split("if(r->args[0]==0)",1)[0]
assert "wol_decode_draw_geometry(r," in hook
assert "glDrawElements(geometry.primitive" in hook
assert "glDrawArrays(GL_TRIANGLE_STRIP" not in hook
print("PASS real hook uses decoded indices and preserves primitive")

#!/usr/bin/env python3
"""Compile the real substituted-draw attribute binding with two-stream fixtures.
GL calls are recorded; vertex data and descriptor decoding follow the real ABI.
"""
import os
from pathlib import Path
import subprocess
import sys
import tempfile

source = Path(sys.argv[1]).read_text()
start = source.index('                if(pair_vbo) {\n                    /* Bind attributes from the GUEST')
end = source.index('                /* WOL_COLOR_STATE:', start)
binding = source[start:end]
helper = ''
if '/* WOL_PAIR_STREAMS_BEGIN */' in source:
    helper = source.split('/* WOL_PAIR_STREAMS_BEGIN */', 1)[1].split('/* WOL_PAIR_STREAMS_END */', 1)[0]
preamble = r'''
#include <assert.h>
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <setjmp.h>
#include <inttypes.h>
typedef unsigned GLuint;
typedef int GLint;
typedef int GLsizei;
typedef size_t GLsizeiptr;
#define GL_ARRAY_BUFFER 1
#define GL_STREAM_DRAW 2
#define GL_FLOAT 3
#define GL_UNSIGNED_BYTE 4
#define GL_FALSE 0
#define GL_TRUE 1
#define PROT_READ 1
struct nvn_vertex_format {unsigned components,type,normalized,bytes;};
struct nvn_vertex_format nvn_vertex_format_decode(unsigned f) {
    return f==0x22?(struct nvn_vertex_format){3,GL_FLOAT,0,12}:
           f==0x16?(struct nvn_vertex_format){2,GL_FLOAT,0,8}:
           (struct nvn_vertex_format){0,0,0,0};
}
struct {unsigned attributes;} nvn_device={4};
struct {unsigned attrib_count,stream_count;uint32_t attrib[16];uint64_t streams[32][2];
        struct {uint64_t address,size;} vertex[32];} nvn_render;
uint64_t nvn_caller;
jmp_buf failure;
const char *last_stop;
void stop(const char *s,uint64_t pc,uint64_t d,int rc) {
    (void)pc;(void)d;(void)rc;last_stop=s;longjmp(failure,1);
}
void *nvn_gpu_pointer(uint64_t p,uint64_t n,unsigned perm) {
    (void)n;(void)perm;return (void *)(uintptr_t)p;
}
struct {GLuint buffer;GLsizei stride;uintptr_t offset;} attrs[4];
struct {const void *data;size_t size;} uploads[64];
GLuint bound,next_buffer=8;
void glGenBuffers(int n,GLuint *ids) {while(n--)*ids++=next_buffer++;}
void glBindBuffer(unsigned type,GLuint id) {(void)type;bound=id;}
void glBufferData(unsigned type,size_t size,const void *p,unsigned usage) {
    (void)type;(void)usage;assert(bound<64);uploads[bound].data=p;uploads[bound].size=size;
}
void glEnableVertexAttribArray(unsigned i) {(void)i;}
void glVertexAttribPointer(unsigned i,int n,unsigned type,unsigned norm,int stride,const void *p) {
    (void)n;(void)type;(void)norm;assert(i<4);attrs[i].buffer=bound;attrs[i].stride=stride;attrs[i].offset=(uintptr_t)p;
}
'''
cases = r'''
void exercise(int direct) {
    static uint8_t positions[64*40],uvs[64*24];
    memset(attrs,0,sizeof attrs);memset(uploads,0,sizeof uploads);
    memset(&nvn_render,0,sizeof nvn_render);
    nvn_render.attrib_count=2;nvn_render.stream_count=2;
    nvn_render.attrib[0]=64|(0x22u<<21);
    nvn_render.attrib[1]=64|1|(16u<<7)|(0x16u<<21);
    nvn_render.streams[0][0]=40;nvn_render.streams[1][0]=24;
    nvn_render.vertex[0].address=(uintptr_t)positions;nvn_render.vertex[0].size=sizeof positions;
    nvn_render.vertex[1].address=(uintptr_t)uvs;nvn_render.vertex[1].size=sizeof uvs;
    uint64_t first=4,vertex_count=48;
    unsigned long long stride=40;
    const uint8_t *base=positions+first*stride;
    GLuint pair_vbo=direct?0:7;
    GLuint pair_stream_vbo[32]={0};pair_stream_vbo[0]=pair_vbo;
    (void)pair_stream_vbo;(void)first;(void)vertex_count;
    glBindBuffer(GL_ARRAY_BUFFER,pair_vbo);
    BINDING
    assert(attrs[0].stride==40);
    assert(attrs[1].stride==24 && "UV attribute must use stream 1 stride, not stream 0 stride");
    if(direct) {
        assert(attrs[0].offset==(uintptr_t)(positions+first*40));
        assert(attrs[1].offset==(uintptr_t)(uvs+first*24+16));
        puts("PASS direct multistream: independent stream base, stride and offset");
    } else {
        assert(attrs[0].buffer==7 && attrs[0].offset==0);
        assert(attrs[1].buffer!=7 && attrs[1].buffer>0 && attrs[1].offset==16);
        assert(uploads[attrs[1].buffer].data==uvs+first*24);
        assert(uploads[attrs[1].buffer].size==vertex_count*24);
        puts("PASS VBO multistream: UVs uploaded from stream 1 with baseVertex");
    }
}
int main(void) {exercise(0);exercise(1);return 0;}
'''.replace('BINDING', binding)
with tempfile.TemporaryDirectory(prefix='wol-streams-', dir=os.environ.get('TMPDIR')) as tmp:
    c = Path(tmp)/'streams.c'
    c.write_text(preamble+helper+cases)
    exe = Path(tmp)/'streams'
    subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror','-O1',str(c),'-o',str(exe)],check=True)
    subprocess.run([str(exe)],check=True)
print('PASS actual hook binds the guest descriptor stream, not only its offset')

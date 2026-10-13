#!/usr/bin/env python3
"""Regression tests for observed transparent-overlay alpha and blend state."""
from pathlib import Path
from types import SimpleNamespace
import os,re,subprocess,sys,tempfile
root=Path(sys.argv[1])
shader=(root/'nvn_shaders.h').read_text().split('static const char wol_pair2_vertex_glsl[]',1)[1].split('static const char wol_pair_fragment_glsl[]',1)[0]
expr=re.search(r'v8 = vec4\(a_col\.rgb,\s*([^;]+)\);',shader).group(1)
for alpha,scale in [(0,1),(0.5,0.8),(1,0.25)]:
    values=[0.0]*96;values[35]=scale
    result=eval(expr,{'__builtins__':{}},{'a_col':SimpleNamespace(a=alpha),'a_pos':SimpleNamespace(w=1.0),'c3':values})
    assert abs(result-alpha*scale)<1e-6, ('vertex alpha must use color.a',alpha,scale,result)
print('PASS sprite alpha 0, fractional, scaled')
s=(root/'nvn_render.h').read_text()
assert s.count('/* WOL_COLOR_STATE_BEGIN */')==1,'expected one unconditional definition'
assert s.index('/* WOL_COLOR_STATE_BEGIN */')<s.index('static GLenum nvn_stencil_operation'),'definition must sit outside the game-conditional blocks'
code=s.split('/* WOL_COLOR_STATE_BEGIN */')[1].split('/* WOL_COLOR_STATE_END */')[0]
assert 'glEnable(GL_BLEND)' in code and 'glDisable(GL_BLEND)' in code
assert 'nvn_render_color_mask(mask&15U)' in code
assert 'nvn_render_state.valid&=~' in code
pre=r'''
#include <stdint.h>
#include <assert.h>
#include <stdio.h>
typedef unsigned GLenum;
#define GL_BLEND 1
enum {NCS_PROGRAM,NCS_BLEND_ENABLE,NCS_BLEND_FUNC,NCS_BLEND_EQUATION,NCS_DEPTH_ENABLE,NCS_DEPTH_FUNC,
      NCS_DEPTH_MASK,NCS_STENCIL_ENABLE,NCS_FRONT_FACE,NCS_CULL_ENABLE,NCS_CULL_FACE,NCS_COLOR_MASK};
static unsigned enable,f[4],e[2],m[4];
static struct {unsigned valid;} nvn_render_state={~0u};
static void glEnable(unsigned x){assert(x==GL_BLEND);enable=1;}
static void glDisable(unsigned x){assert(x==GL_BLEND);enable=0;}
static void glBlendFuncSeparate(unsigned a,unsigned b,unsigned c,unsigned d){f[0]=a;f[1]=b;f[2]=c;f[3]=d;}
static void glBlendEquationSeparate(unsigned a,unsigned b){e[0]=a;e[1]=b;}
static void nvn_render_state_epoch(void){}
static void nvn_render_color_mask(unsigned x){m[0]=x&1;m[1]=(x>>1)&1;m[2]=(x>>2)&1;m[3]=(x>>3)&1;}
static unsigned nvn_blend_factor(unsigned x){return x;}
static unsigned nvn_blend_equation(unsigned x){return x;}
'''
post=r'''
int main(void){
    /* observed run-166/167 sprite state: SRC_ALPHA, ONE_MINUS_SRC_ALPHA, FUNC_ADD, full mask */
    wol_apply_color_state(0x803ff00,0x06050605,0x110c0007,15);
    assert(enable && f[0]==5 && f[1]==6 && f[2]==5 && f[3]==6);
    assert(e[0]==1 && e[1]==1 && m[0] && m[1] && m[2] && m[3]);
    assert(!(nvn_render_state.valid&(1u<<NCS_BLEND_ENABLE)));
    assert(!(nvn_render_state.valid&(1u<<NCS_BLEND_FUNC)));
    assert(!(nvn_render_state.valid&(1u<<NCS_BLEND_EQUATION)));
    assert(!(nvn_render_state.valid&(1u<<NCS_COLOR_MASK)));
    puts("PASS sprite SRC_ALPHA/ONE_MINUS_SRC_ALPHA is applied and slots invalidated");
    wol_apply_color_state(0,0x02010201,0x32000000,5);
    assert(!enable);
    assert(m[0] && !m[1] && m[2] && !m[3]);
    puts("PASS disabled blend keeps the write mask contract");
    /* Review 2026-10-14: mask-value contract for the four observed classes. */
    wol_apply_color_state(0,0,0,15);
    assert(m[0] && m[1] && m[2] && m[3]);
    wol_apply_color_state(0,0,0,0);
    assert(!m[0] && !m[1] && !m[2] && !m[3]);
    puts("PASS write mask 0x0/0xf map to full off/on");
    return 0;
}
'''
with tempfile.TemporaryDirectory(prefix='wol-color-',dir=os.environ.get('TMPDIR')) as tmp:
    c=Path(tmp)/'probe.c';exe=Path(tmp)/'probe';c.write_text(pre+code+post)
    subprocess.run(['cc','-std=c11','-Wall','-Wextra','-Werror',str(c),'-o',str(exe)],check=True)
    subprocess.run([str(exe)],check=True)
hook=s.split('static void nvn_render_draw_inner(struct nvn_record *r)',1)[1].split('static void nvn_render_draw(struct nvn_record *r)',1)[0]
call='wol_apply_color_state(nvn_render.color,nvn_render.blend[1],nvn_render.blend[0],nvn_render.mask&15U)'
call2='wol_apply_color_state(nvn_render.color,nvn_render.blend[1],nvn_render.blend[0],wol_mask_bits)'
assert hook.count(call)+hook.count(call2)>=2,'pair path and standard path must both apply the guest color contract'
print('PASS pair-path and standard draw hooks apply the guest color contract')
# Review 2026-10-14 regression guards:
assert 'if(mih&&!wol_mask_bits&&nvn_render.mask)wol_mask_bits=(nvn_render.mask>>4)&15U;' in hook,\
    'the high-nibble heuristic must only fire when configured, low nibble empty and value nonzero'
assert 'nvn_vertex_format_decode(format)' in hook,\
    'vertex attributes must bind from the guest descriptors (stride-60 color@24/uv@28 regression)'
assert hook.count('glVertexAttribPointer(i,(GLint)vf.components,vf.type,vf.normalized')>=2,\
    'both VBO and direct paths must use the descriptor-driven binding'
assert 'wol_trace_this=0;' in hook and 'if(wol_trace_this) {' in hook,\
    'before/after trace sections must share one per-draw flag'
print('PASS regression guards: mask heuristic scope, descriptor binding, trace pairing')

#!/usr/bin/env python3
"""Regression for the decoded f309/f08 skinned-mesh UV contract.
The display composite and the mesh share code hashes but have distinct control
identities. The composite's clip-derived sampling must never leak into meshes.
"""
from pathlib import Path
from types import SimpleNamespace
import math
import re
import sys

s=Path(sys.argv[1]).read_text()
vertex=s.split('static const char wol_pair_vertex_glsl[] =',1)[1].split('static const char wol_pair2_vertex_glsl[] =',1)[0]
m=re.search(r'v8 = vec2\((.+?), (.+?)\);',vertex)
assert m, 'missing UV varying assignment'
for uv,st in [((.25,.75),(1.,1.,0.,0.)),((.37,.62),(2.26285719871521,1.0181818008422852,-.6000000238418579,-.008080808445811272))]:
    c3=[0.]*96;c3[32:36]=st
    scope={'a_extra':SimpleNamespace(x=uv[0],y=uv[1]),'a_pos':SimpleNamespace(z=19.),'c3':c3}
    actual=tuple(eval(expr,{'__builtins__':{}},scope) for expr in m.groups())
    expected=(uv[0]*st[0]+st[2],uv[1]*st[1]+st[3])
    assert all(math.isclose(a,b,abs_tol=1e-7) for a,b in zip(actual,expected)), ('mesh UV must use both input UV lanes and the material ST',actual,expected)
print('PASS PC torso and Cactus Bill UVs use x/y plus per-material scale/offset, not position.z')
match=re.search(r'/\*5\*/[^\n]*"f08bad2f#c320",(\w+),',s)
assert match, 'missing skinned-mesh fragment identity'
entry=match.group(1)
frag=s.split('static const char '+entry+'[] =',1)[1].split(';\n',1)[0]
assert 'texture2D(tex0, v8)' in frag, 'mesh fragment must use its perspective-correct UV varying'
assert 'v7.xy' not in frag and 'v7.w' not in frag, 'clip-position composite coordinates are invalid for a mesh'
print('PASS mesh fragment samples its own UVs, without a second perspective divide')
assert 'else if(!strcmp(bf->name,"f08bad2f#a9b0"))' in s, 'composite sampling override must match exact composite control identity'
print('PASS composite override excludes f08bad2f#c320')

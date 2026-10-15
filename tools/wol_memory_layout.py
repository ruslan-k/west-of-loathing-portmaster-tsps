#!/usr/bin/env python3
"""Compile descriptor offsetof/sizeof from exact build source; bind to ELF SHA.

Usage: wol_memory_layout.py BUILD_DIR OUT.json
Requires native cc and nm; never copies hardcoded offsets between builds.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import re
import subprocess
import tempfile

FIELDS = {
 'texture': ('object id size b.width b.height b.depth b.levels b.format b.flags b.target b.offset b.pool pool name depth_buffer live references draws zero_storage host_scaled host_width host_height cpu_snapshot zero_backend_deferred host_upload_type').split(),
 'pool': 'object address size generation flags references live retired owned'.split(),
 'region': 'base size perm state attr'.split(),
}


def declaration(text, name):
    m = re.search(r'\bstruct\s+' + re.escape(name) + r'\s*\{', text)
    if not m:
        raise ValueError('missing struct ' + name)
    # Structs here contain no nested definitions; comments can contain braces.
    clean = re.sub(r'/\*.*?\*/|//[^\n]*', '', text[m.start():], flags=re.S)
    end = clean.index('}')
    return clean[:end + 1] + ';\n'


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('build', type=Path)
    ap.add_argument('out', type=Path)
    a = ap.parse_args()
    native = a.build / 'source/native'
    sources = [(native/'t2_page_wrap.h', 't2_page_wrap_cache'),
               (native/'t2_page_substitution.h', 't2_page_state'),
               (native/'nvn_textures.h', 'nvn_texture_builder'),
               (native/'nvn_textures.h', 'nvn_texture'),
               (native/'nvn_memory.h', 'nvn_pool'),
               (native/'loader.c', 'region')]
    code = '#include <stdint.h>\n#include <stddef.h>\n#include <stdio.h>\ntypedef unsigned GLuint,GLenum;typedef int GLint;typedef float GLfloat;typedef void *EGLContext;\n'
    for path, name in sources:
        code += declaration(path.read_text(), name)
    code += 'int main(void){\n'
    for kind, names in FIELDS.items():
        typ = 'nvn_' + kind if kind != 'region' else 'region'
        code += f'printf("{kind}_size %zu\\n", sizeof(struct {typ}));\n'
        for name in names:
            code += f'printf("{kind} {name} %zu %zu\\n", offsetof(struct {typ},{name}),sizeof(((struct {typ}*)0)->{name}));\n'
    code += '}\n'
    scratch = os.environ.get('TMPDIR')
    with tempfile.TemporaryDirectory(prefix='wol-layout-', dir=scratch) as td:
        c = Path(td)/'layout.c'
        c.write_text(code)
        exe = Path(td)/'layout'
        subprocess.run(['cc', '-std=c11', '-Wall', '-Wextra', '-Werror', str(c), '-o', str(exe)], check=True)
        stdout = subprocess.check_output([str(exe)], text=True)
    elf = a.build/'wol-horizon'
    result: dict = dict(schema=1, elf_sha256=hashlib.sha256(elf.read_bytes()).hexdigest(), symbols={},
                  texture={}, pool={}, region={}, source_sha256={str(p.relative_to(native)):hashlib.sha256(p.read_bytes()).hexdigest() for p,_ in sources})
    for line in stdout.splitlines():
        p = line.split()
        if len(p) == 2:
            result[p[0]] = int(p[1])
        else:
            result[p[0]][p[1]] = [int(p[2]), int(p[3])]
    wanted = {'heap_size','nregions','regions','nvn_textures','nvn_textures_high','nvn_pools'}
    for line in subprocess.check_output(['nm','-S','--defined-only',str(elf)], text=True).splitlines():
        p = line.split()
        if len(p) == 4 and p[3] in wanted:
            result['symbols'][p[3]] = dict(offset=int(p[0],16), size=int(p[1],16))
    if set(result['symbols']) != wanted:
        raise ValueError('required BSS symbols unavailable; use the unstripped exact ELF')
    if result['symbols']['nvn_textures']['size'] % result['texture_size'] or result['symbols']['nvn_pools']['size'] != 256*result['pool_size']:
        raise ValueError('compiled layout disagrees with ELF symbol sizes')
    a.out.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k: result[k] for k in ('elf_sha256','texture_size','pool_size','region_size')}, indent=2))

if __name__ == '__main__':
    main()

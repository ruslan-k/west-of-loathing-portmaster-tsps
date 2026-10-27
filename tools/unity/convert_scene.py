#!/usr/bin/env python3
"""Convert WoL's two-node scene with pmunity's existing single-file steps."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from pmunity.unity_io import load

root = Path(sys.argv[1]).resolve()
source = root / 'data/StreamingAssets/main_scene'
work = root / 'scene-data'
original = load(str(source))
bundle = original.file
names = list(bundle.files)
assert len(names) == 2 and all(type(f).__name__ == 'SerializedFile' for f in bundle.files.values()), names
shared = next(n for n, f in bundle.files.items() if any(o.type.name == 'Shader' for o in f.objects.values()))
scene = next(n for n in names if n != shared)
assert not any(o.type.name in ('Shader', 'Texture2D') for o in bundle.files[scene].objects.values())
# shortcut: this scene has inline textures and no resource nodes; refuse other bundle shapes.
for o in bundle.files[shared].objects.values():
    if o.type.name == 'Texture2D':
        assert not o.read_typetree().get('m_StreamData', {}).get('size', 0)
before = {(n, pid): o.get_raw_data() for n, f in bundle.files.items() for pid, o in f.objects.items()
          if o.type.name not in ('Shader', 'Texture2D')}
textures = {pid: (o.read_typetree()['m_Width'], o.read_typetree()['m_Height'])
            for pid, o in bundle.files[shared].objects.items() if o.type.name == 'Texture2D'}
work.mkdir(exist_ok=False)
(work / 'sharedassets0.assets').write_bytes(bundle.files[shared].save())
shutil.copy2(root / 'data/globalgamemanagers', work / 'globalgamemanagers')
subprocess.run([sys.executable, '-m', 'pmunity', 'convert', str(work), '--config', str(Path(__file__).resolve().parent / 'convert.json')], check=True)
converted = load(str(work / 'sharedassets0.assets'))
converted.file.flags = bundle.files[shared].flags
bundle.files[shared] = converted.file
candidate = source.with_suffix('.converted')
candidate.write_bytes(bundle.save(packer='lz4'))
check = load(str(candidate)).file
assert list(check.files) == names
for n, f in check.files.items():
    for pid, o in f.objects.items():
        if (n, pid) in before:
            assert o.get_raw_data() == before[(n, pid)], (n, pid, o.type.name)
        if n == shared and pid in textures:
            t = o.read_typetree()
            assert (t['m_Width'], t['m_Height']) == textures[pid]
        if o.type.name == 'Shader':
            t = o.read_typetree()
            assert 9 in t['platforms'], (pid, t['m_ParsedForm']['m_Name'], t['platforms'])
report = {'nodes': names, 'non_texture_shader_objects_preserved': len(before), 'texture_dimensions_preserved': len(textures),
          'shader_count': sum(o.type.name == 'Shader' for o in check.files[shared].objects.values())}
(root / 'scene-conversion-check.json').write_text(json.dumps(report, indent=2) + '\n')
os.replace(candidate, source)
print(json.dumps(report))

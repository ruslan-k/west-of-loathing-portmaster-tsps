#!/usr/bin/env python3
"""Build exactly once from a freshly regenerated, verified WoL overlay."""
from pathlib import Path
import difflib
import hashlib
import subprocess
import sys

repo = Path(__file__).resolve().parents[1]
spike = Path('/mnt/external/Hermes/spikes/wol-switch')
base, src = spike/'upstream-source', spike/'wol-horizon-source'
name = sys.argv[1]
assert name.startswith('wol-horizon-build-') and '/' not in name
out = spike/name
assert not out.exists(), out
patch = repo/'runtime/wol-adapter.patch'
from wol_overlay_verify import generate, verify
previous = patch.read_text()
text = generate(base, src)
assert 'WOL_DRAW_GEOMETRY' in text
patch.write_text(text)
parity = verify(base, src, patch)
print('SOURCE_PARITY', len(parity['native_files']), flush=True)
print('OVERLAY',len(text),hashlib.sha256(text.encode()).hexdigest(),flush=True)
args=['docker','run','--rm','--security-opt','label=disable','-v',str(spike)+':/workspace',
      '-v',str(repo)+':/work','--entrypoint','/bin/sh','pmjs-arm64-spruce-local:20261002-gcc10',
      '-c','cd /work && bash build_horizon.sh /workspace/upstream-source /workspace/wol-horizon-image /workspace/'+name]
log=spike/(name+'.log')
with log.open('w') as f:
    result=subprocess.run(args,stdout=f,stderr=subprocess.STDOUT)
print('BUILD_RC',result.returncode,'LOG',log,flush=True)
if result.returncode:
    print('\n'.join(log.read_text().splitlines()[-60:]))
    raise SystemExit(result.returncode)
elf=out/'wol-horizon'
data=elf.read_bytes()
assert data[:4]==b'\x7fELF'
assert b'WOL_DRAW_GEOMETRY op=' in data
print('ELF',elf,'BYTES',len(data),'SHA256',hashlib.sha256(data).hexdigest(),flush=True)

#!/usr/bin/env python3
"""M6 side-cache builder: BC textures in the WoL core bundle -> ASTC 6x6 cache.

Roadmap section 6, step 3 (owner-local content-hash cache). This tool is the host side:
it selects BC textures from the M2/M4 manifest, decodes them to RGBA with UnityPy,
computes the content hash the runtime can reproduce (sha256 over the RGBA8 pixels),
encodes ASTC 6x6 with astcenc and writes one cache file plus an audit.

Cache file format (little endian):
  'WOL6'      magic u32
  version=1   u32
  n           u32            entries
  entry[0..n): hash[32] | width u32 | height u32 | block u8 | gl_enum u32 | levels u8 |
               payload_len u32 | payload_offset u64 | reserved[6] u8  (fixed 64 bytes)
  payloads    raw ASTC block streams (no .astc file header), 16-byte blocks

Only single-level textures are supported in this first version (M4 stripped targets are
single-level; anything with mips is deferred and reported in the audit). Keying by RGBA
content lets the runtime hash what its own decoder produced, so the cache stays correct
even if the guest's tiled source layout differs (see cache-design.md).
"""
from pathlib import Path
import argparse
import hashlib
import json
import struct
import subprocess
import sys

import UnityPy

BLOCK = 6
GL_ENUM_ASTC_6x6 = 0x93B4


def astc_encode(astcenc_cmd, png, out_astc):
    cmd = astcenc_cmd.split() + ['-cl', str(png), str(out_astc), f'{BLOCK}x{BLOCK}', '-medium']
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f'astcenc failed for {png}: {r.stdout} {r.stderr}')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--bundle', type=Path, required=True, help='core bundle (current accepted layout)')
    ap.add_argument('--manifest', type=Path, required=True, help='repack manifest tsv (name/format/sizes)')
    ap.add_argument('--out', type=Path, required=True, help='cache .bin path')
    ap.add_argument('--audit', type=Path, required=True, help='audit json path')
    ap.add_argument('--top', type=int, default=24, help='how many textures to include (largest first)')
    ap.add_argument('--tmpdir', type=Path, default=None, help='work dir for png/astc files (visible to astcenc)')
    ap.add_argument('--astcenc', default='astcenc', help="encoder command, e.g. 'docker exec astc-tool astcenc' with --tmpdir under /work")
    ap.add_argument('--astc-prefix', default='', help='path prefix the encoder sees for --tmpdir files (e.g. /work/m6-cache-work)')
    a = ap.parse_args()

    tmp = a.tmpdir or a.out.parent / 'work'
    tmp.mkdir(parents=True, exist_ok=True)

    # select: BC-class formats, largest serialised payloads first
    sel = []
    with a.manifest.open() as f:
        head = f.readline().split('\t')
        for line in f:
            parts = line.rstrip('\n').split('\t')
            if len(parts) != len(head):
                continue
            row = dict(zip(head, parts))
            if row['format'] not in ('DXT1', 'DXT5'):
                continue
            sel.append(row)
    sel.sort(key=lambda r: -int(r['payload_before']))
    sel = sel[:a.top]
    wanted = {int(r['path_id']) for r in sel}
    want_names = {r['name']: r for r in sel}

    env = UnityPy.load(str(a.bundle))
    entries, audit = [], []
    rgba_total = astc_total = 0
    for obj in env.objects:
        if obj.type.name != 'Texture2D' or obj.path_id not in wanted:
            continue
        d = obj.read()
        row = want_names.get(d.m_Name)
        rec = dict(path_id=obj.path_id, name=d.m_Name, fmt=str(d.m_TextureFormat),
                   width=d.m_Width, height=d.m_Height)
        if getattr(d, 'm_MipCount', 1) not in (0, 1):
            rec['skip'] = f'mips={d.m_MipCount} deferred'
            audit.append(rec)
            continue
        img = d.image.convert('RGBA')
        rgba = img.tobytes()
        h = hashlib.sha256(rgba).digest()
        png = tmp / f'{d.m_Name}.png'
        img.save(png)
        astc = tmp / f'{d.m_Name}.astc'
        png_tool = f'{a.astc_prefix}/{png.name}' if a.astc_prefix else str(png)
        astc_tool = f'{a.astc_prefix}/{astc.name}' if a.astc_prefix else str(astc)
        astc_encode(a.astcenc, png_tool, astc_tool)
        payload = astc.read_bytes()[16:]  # strip the .astc file header
        assert len(payload) % 16 == 0
        ents = ((d.m_Width + BLOCK - 1) // BLOCK) * ((d.m_Height + BLOCK - 1) // BLOCK)
        rec.update(rgba_bytes=len(rgba), astc_bytes=len(payload),
                   expected_bytes=ents * 16, hash=h.hex(),
                   payload_fits=(len(payload) == ents * 16))
        if len(payload) != ents * 16:
            rec['skip'] = 'block math mismatch'
            audit.append(rec)
            continue
        entries.append((h, d.m_Width, d.m_Height, payload))
        rgba_total += len(rgba)
        astc_total += len(payload)
        audit.append(rec)

    # write cache
    off = 12 + 64 * len(entries)
    blob = bytearray()
    toc = bytearray()
    for h, w, hh, payload in entries:
        toc += h + struct.pack('<IIBIBIQ6B', w, hh, BLOCK, GL_ENUM_ASTC_6x6, 1, len(payload), off, 0, 0, 0, 0, 0, 0)
        blob += payload
        off += len(payload)
    a.out.write_bytes(b'WOL6' + struct.pack('<II', 1, len(entries)) + bytes(toc) + bytes(blob))

    summary = dict(schema=1, entries=len(entries), skipped=len(audit) - len(entries),
                   rgba_bytes=rgba_total, astc_bytes=astc_total,
                   ratio=round(rgba_total / astc_total, 2) if astc_total else None,
                   cache_bytes=a.out.stat().st_size, textures=audit)
    a.audit.write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps({k: v for k, v in summary.items() if k != 'textures'}, indent=2))


if __name__ == '__main__':
    main()

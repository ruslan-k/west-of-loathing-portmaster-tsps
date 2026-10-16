#!/usr/bin/env python3
"""M6 side-cache builder: BC textures in the WoL core bundle -> ASTC 6x6 cache.

Roadmap section 6, step 3 (owner-local content-hash cache), host side. Selects BC
textures from the repack manifest, produces the RGBA8 the runtime decoder would produce
(--bcdec-tool, the exact vendor/bcdec replica; UnityPy stays available as a fallback but
its rounding differs and the runtime will not match it), computes the sha256 over those
pixels, encodes ASTC 6x6 with astcenc and writes one cache file plus an audit.

Cache file format (little endian; see evidence/m6-compressed-textures/cache-design.md):
  'WOL6' u32 | version=1 u32 | n u32
  entry (64 B): sha256[32] | width u32 | height u32 | block u8 | gl_enum u32 | levels u8 |
                payload_len u32 | payload_offset u64 | reserved[6]
  payloads: raw ASTC block streams (no .astc header).
Single-level textures only in v1 (M4-stripped targets); multi-mip textures are skipped
and listed in the audit.
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
NVN_FMT = {'DXT1': 0x41, 'DXT5': 0x44}


def astc_encode(astcenc_cmd, png, out_astc):
    cmd = astcenc_cmd.split() + ['-cl', str(png), str(out_astc), f'{BLOCK}x{BLOCK}', '-medium']
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f'astcenc failed for {png}: {r.stdout} {r.stderr}')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--bundle', type=Path, required=True)
    ap.add_argument('--manifest', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True, help='cache .bin path')
    ap.add_argument('--audit', type=Path, required=True)
    ap.add_argument('--top', type=int, default=24)
    ap.add_argument('--min-side', type=int, default=0)
    ap.add_argument('--tmpdir', type=Path, default=None)
    ap.add_argument('--astcenc', default='astcenc')
    ap.add_argument('--astc-prefix', default='')
    ap.add_argument('--bcdec-tool', default='', help='bcdecode_host binary (runtime-canon decode); strongly recommended')
    a = ap.parse_args()

    tmp = a.tmpdir or a.out.parent / 'work'
    tmp.mkdir(parents=True, exist_ok=True)
    assert a.bcdec_tool, ('--bcdec-tool is required: the cache must be keyed by the runtime '
                          "decoder's output, a different decoder's rounding never matches")

    sel = []
    with a.manifest.open() as f:
        head = f.readline().split('\t')
        for line in f:
            parts = line.rstrip('\n').split('\t')
            if len(parts) != len(head):
                continue
            row = dict(zip(head, parts))
            if row['format'] not in NVN_FMT:
                continue
            if a.min_side and min(int(row['width']), int(row['height'])) < a.min_side:
                continue
            sel.append(row)
    sel.sort(key=lambda r: -int(r['payload_before']))
    sel = sel[:a.top]
    by_pid = {int(r['path_id']): r for r in sel}

    env = UnityPy.load(str(a.bundle))
    plan, audit = [], []
    for obj in env.objects:
        if obj.type.name != 'Texture2D' or obj.path_id not in by_pid:
            continue
        d = obj.read()
        rec = dict(path_id=obj.path_id, name=d.m_Name, fmt=str(d.m_TextureFormat),
                   width=d.m_Width, height=d.m_Height)
        if getattr(d, 'm_MipCount', 1) not in (0, 1):
            rec['skip'] = f'mips={d.m_MipCount} deferred'
            audit.append(rec)
            continue
        raw = bytes(d.image_data)
        fmt_hex = NVN_FMT[by_pid[obj.path_id]['format']]
        blocks = ((d.m_Width + 3) // 4) * ((d.m_Height + 3) // 4)
        raw = raw[:blocks * (8 if fmt_hex in (0x41, 0x42) else 16)]
        if len(raw) != blocks * (8 if fmt_hex in (0x41, 0x42) else 16):
            rec['skip'] = 'short level-0 payload'
            audit.append(rec)
            continue
        rec['fmt_nvn'] = hex(fmt_hex)
        plan.append((rec, raw))

    if not plan:
        raise SystemExit('nothing selected')

    # decode with the runtime canon (bcdecode_host = vendor/bcdec replica)
    in_dir = tmp / 'catalog-in'
    out_dir = tmp / 'catalog-out'
    for d in (in_dir, out_dir):
        if d.exists():
            for f in d.iterdir():
                f.unlink()
        d.mkdir(parents=True, exist_ok=True)
    for rec, raw in plan:
        fmt_hex = int(rec['fmt_nvn'], 16)
        name = f"{rec['width']}x{rec['height']}-{fmt_hex:x}-{rec['path_id']}.bc"
        (in_dir / name).write_bytes(raw)
        rec['bc_file'] = name
    r = subprocess.run([a.bcdec_tool, str(in_dir), str(out_dir)], capture_output=True, text=True)
    print(r.stdout.strip() or r.stderr.strip())
    if r.returncode != 0:
        raise SystemExit('bcdecode_host failed')

    entries, rgba_total, astc_total = [], 0, 0
    for rec, raw in plan:
        w, h = rec['width'], rec['height']
        fmt_hex = int(rec['fmt_nvn'], 16)
        rgba = (tmp / 'catalog-out' / f"{w}x{h}-{fmt_hex:x}-{rec['path_id']}.rgba").read_bytes()
        rec['rgba_bytes'] = len(rgba)
        hh = hashlib.sha256(rgba).digest()
        png = tmp / f"{rec['name']}.png"
        astc = tmp / f"{rec['name']}.astc"
        png_tool = f"{a.astc_prefix}/{png.name}" if a.astc_prefix else str(png)
        astc_tool = f"{a.astc_prefix}/{astc.name}" if a.astc_prefix else str(astc)
        from PIL import Image
        Image.frombytes('RGBA', (w, h), rgba).save(png)
        astc_encode(a.astcenc, png_tool, astc_tool)
        payload = astc.read_bytes()[16:]
        ents = ((w + BLOCK - 1) // BLOCK) * ((h + BLOCK - 1) // BLOCK)
        rec['astc_bytes'] = len(payload)
        rec['expected_bytes'] = ents * 16
        rec['hash'] = hh.hex()
        if len(payload) != ents * 16:
            rec['skip'] = 'block math mismatch'
            audit.append(rec)
            continue
        entries.append((hh, w, h, payload))
        rgba_total += rec['rgba_bytes']
        astc_total += len(payload)
        audit.append(rec)

    off = 12 + 64 * len(entries)
    blob, toc = bytearray(), bytearray()
    for hh, w, h, payload in entries:
        toc += hh + struct.pack('<IIBIBIQ6B', w, h, BLOCK, GL_ENUM_ASTC_6x6, 1, len(payload), off, 0, 0, 0, 0, 0, 0)
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

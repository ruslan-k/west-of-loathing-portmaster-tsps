#!/usr/bin/env python3
"""M6 E2E test cache: null (zero) BC payloads for every (w,h,fmt) in the bundle.

In the m1m5 route (menu + stationary street) every runtime BC texture is created with
zero content (no guest flush ever fills them), so a content cache built from the bundle
can never hit there. This builder fabricates the exact bytes the runtime decoder produces
for zeroed BC blocks, for every (w,h,fmt) combination present in the manifest, and encodes
those as ASTC. Hitting these entries proves the whole mechanism end-to-end on the device
(load -> hash -> lookup -> glCompressedTexImage2D -> sampled pixels) and yields a memory
signal on the empty textures; it is a mechanism proof, not a content optimization.

Output: WOL6 cache (see cache-design.md) + a small JSON report.
"""
from pathlib import Path
import argparse
import csv
import hashlib
import json
import struct
import subprocess

from PIL import Image

BLOCK = 6
GL_ENUM_ASTC_6x6 = 0x93B4


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--manifest', type=Path, required=True)
    ap.add_argument('--bcdec-tool', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--report', type=Path, required=True)
    ap.add_argument('--workdir', type=Path, required=True)
    ap.add_argument('--astcenc', default='astcenc')
    ap.add_argument('--astc-prefix', default='')
    a = ap.parse_args()

    combos = set()
    with a.manifest.open() as f:
        for r in csv.DictReader(f, delimiter='\t'):
            if r['format'] in ('DXT1', 'DXT5'):
                combos.add((int(r['width']), int(r['height']),
                            0x41 if r['format'] == 'DXT1' else 0x44))
    combos = sorted(combos)

    in_dir = a.workdir / 'in'
    out_dir = a.workdir / 'out'
    for d in (in_dir, out_dir):
        d.mkdir(parents=True, exist_ok=True)
        for f in d.iterdir():
            f.unlink()

    for w, h, fmt in combos:
        block = 8 if fmt == 0x41 else 16
        blocks = ((w + 3) // 4) * ((h + 3) // 4)
        (in_dir / f'{w}x{h}-{fmt:x}-0.bc').write_bytes(b'\0' * (blocks * block))

    r = subprocess.run([str(a.bcdec_tool), str(in_dir), str(out_dir)], capture_output=True, text=True)
    print(r.stdout.strip() or r.stderr.strip())
    if r.returncode != 0:
        raise SystemExit('bcdecode_host failed')

    entries, report = [], []
    for w, h, fmt in combos:
        rgba = (out_dir / f'{w}x{h}-{fmt:x}-0.rgba').read_bytes()
        assert len(rgba) == w * h * 4, (w, h, fmt, len(rgba))
        hh = hashlib.sha256(rgba).digest()
        png = a.workdir / f'n{w}x{h}-{fmt:x}.png'
        astc = a.workdir / f'n{w}x{h}-{fmt:x}.astc'
        Image.frombytes('RGBA', (w, h), rgba).save(png)
        png_tool = f'{a.astc_prefix}/{png.name}' if a.astc_prefix else str(png)
        astc_tool = f'{a.astc_prefix}/{astc.name}' if a.astc_prefix else str(astc)
        enc = subprocess.run(a.astcenc.split() + ['-cl', png_tool, astc_tool, f'{BLOCK}x{BLOCK}', '-medium'],
                             capture_output=True, text=True)
        if enc.returncode != 0:
            raise SystemExit(f'astcenc failed {w}x{h}: {enc.stdout} {enc.stderr}')
        payload = astc.read_bytes()[16:]
        ents = ((w + BLOCK - 1) // BLOCK) * ((h + BLOCK - 1) // BLOCK)
        assert len(payload) == ents * 16, (w, h, len(payload), ents * 16)
        entries.append((hh, w, h, payload))
        report.append(dict(w=w, h=h, fmt=hex(fmt), hash=hh.hex(), astc_bytes=len(payload)))

    off = 12 + 64 * len(entries)
    toc, blob = bytearray(), bytearray()
    for hh, w, h, payload in entries:
        toc += hh + struct.pack('<IIBIBIQ6B', w, h, BLOCK, GL_ENUM_ASTC_6x6, 1, len(payload), off, 0, 0, 0, 0, 0, 0)
        blob += payload
        off += len(payload)
    a.out.write_bytes(b'WOL6' + struct.pack('<II', 1, len(entries)) + bytes(toc) + bytes(blob))

    total = sum(len(e[3]) for e in entries)
    a.report.write_text(json.dumps(dict(schema=1, entries=len(entries), astc_bytes=total,
                                        cache_bytes=a.out.stat().st_size, combos=report), indent=1) + '\n')
    print(f"WROTE {a.out} entries={len(entries)} astc_bytes={total} cache_bytes={a.out.stat().st_size}")


if __name__ == '__main__':
    main()

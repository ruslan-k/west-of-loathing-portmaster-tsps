"""M9 probe: convert one named Texture2D in a bundle from its block format to
ASTC RGBA 6x6 (Unity TextureFormat 56) using astcenc in the astc-tool
container, and re-serialize the bundle.

The converted texture keeps its dimensions; the serialized data and format
change only. This is a measure-and-learn probe: it answers what NVN format id
the guest passes for an ASTC texture and whether the guest loads it at all.
"""
import argparse
import hashlib
import pathlib
import subprocess
import sys

import UnityPy

ASTC_MAGIC = 0x5CA1AB13


def astc_encode(rel_png: str, rel_astc: str, block: str) -> None:
    r = subprocess.run(
        ['docker', 'exec', 'astc-tool', 'astcenc', '-cl', f'/work/{rel_png}', f'/work/{rel_astc}',
         block, '-medium'],
        capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f'astcenc failed: {r.stdout} {r.stderr}')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('core', type=pathlib.Path)
    ap.add_argument('--name', action='append', required=True,
                    help='texture name; repeat for a batch')
    ap.add_argument('--block', default='6x6')
    ap.add_argument('--out', required=True)
    ap.add_argument('--workdir', default='/mnt/external/Hermes/spikes/wol-switch/m9-probe')
    a = ap.parse_args()
    work = pathlib.Path(a.workdir)
    work.mkdir(parents=True, exist_ok=True)

    env = UnityPy.load(str(a.core))
    wanted = set(a.name)
    found = 0
    for x in env.objects:
        if x.type.name != 'Texture2D':
            continue
        d = x.read()
        if d.m_Name not in wanted:
            continue
        found += 1
        fmt_name = str(d.m_TextureFormat)
        print(f'found {d.m_Name}: format={fmt_name} {d.m_Width}x{d.m_Height} mips={d.m_MipCount} '
              f'image_bytes={len(bytes(d.image_data))}')
        if d.m_MipCount != 1 or d.m_ImageCount != 1:
            print('  SKIP (needs single level, single image)')
            continue
        img = d.image
        png = work / f'{d.m_Name}.png'
        img.save(png)
        astc = work / f'{d.m_Name}.astc'
        astc_encode(f'm9-probe/{png.name}', f'm9-probe/{astc.name}', a.block)
        raw = astc.read_bytes()
        assert int.from_bytes(raw[:4], 'little') == ASTC_MAGIC, 'not an astc file'
        blocks = raw[16:]
        bw, bh = raw[4], raw[5]
        dim_x = raw[7] | (raw[8] << 8) | (raw[9] << 16)
        dim_y = raw[10] | (raw[11] << 8) | (raw[12] << 16)
        assert (dim_x, dim_y) == (d.m_Width, d.m_Height), 'astc dims mismatch'
        cw, ch = (d.m_Width + bw - 1) // bw, (d.m_Height + bh - 1) // bh
        expect = cw * ch * 16
        assert len(blocks) == expect, (len(blocks), expect)
        orig = len(bytes(d.image_data))
        d.m_TextureFormat = 56  # Unity TextureFormat.ASTC_RGBA_6x6
        d.image_data = blocks
        d.m_CompleteImageSize = len(blocks)
        x.save_typetree(d)
        print(f'  -> astc {cw}x{ch} payload={len(blocks)} (was {orig})')
    print(f'converted {found} of {len(wanted)} requested names')
    out = pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    env.save(pack='lz4', out_path=str(out))
    for f in out.iterdir():
        h = hashlib.sha256(f.read_bytes()).hexdigest()[:16]
        print(f'OUT {f.name} {f.stat().st_size} bytes sha256={h}')
    return 0


if __name__ == '__main__':
    sys.exit(main())

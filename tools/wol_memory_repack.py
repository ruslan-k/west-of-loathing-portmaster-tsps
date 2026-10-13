#!/usr/bin/env python3
"""WoL memory repack: promote mip level 1 to level 0 for Texture2D assets with m_Width >= 512.

The Switch bundle (StreamingAssets/core, 200,367,356 bytes) carries 4411 Texture2D whose
decompressed payload totals ~1900 MB - more than the TSPS's 963 MiB RAM, which is why the title
thrashes swap and never finishes loading. Every texture stores a full mip chain, so level 1 (a
properly box-filtered half-resolution copy) already exists in the bytes: re-slicing the chain and
halving m_Width/m_Height/m_MipCount shrinks the payload with **zero re-encoding** and no format
change. Measured on the title's bundle: 1450 textures modified, payload 1899.7 -> 603.2 MB.

The repacked bundle is OWNER DATA: keep inputs/outputs local, never publish them. The deploy
contract (measured): the UnityFS bundle starts at section offset 0x4DB0D0 (0x78000 romfs offset +
0x4630d0 file offset); the runtime verifies the section by SIZE only, the guest parses its own
RomFS metadata, and pad the repacked file with zeros back to exactly 200,367,356 bytes so the
RomFS file entry stays valid.

Usage: python3 wol_memory_repack.py <core> <out_dir> [--min-width 512]
"""
import argparse
import pathlib
import sys
import time

import UnityPy
from UnityPy.enums import TextureFormat

BLOCK = {"DXT1": 8, "BC4": 8, "DXT5": 16, "BC5": 16, "BC6H": 16, "BC7": 16}


def level0_size(w, h, fmt):
    if fmt in BLOCK:
        return max(1, (w + 3) // 4) * max(1, (h + 3) // 4) * BLOCK[fmt]
    if fmt in ("ARGB4444", "RGBA4444", "RGB565"):
        return w * h * 2
    if fmt == "RGBA32":
        return w * h * 4
    if fmt == "RGB24":
        return w * h * 3
    if fmt in ("R8", "Alpha8"):
        return w * h
    if fmt == "RG16":
        # Unity TextureFormat.RG16 = two 8-bit channels (2 bytes/px). The earlier *4 was wrong
        # (review 2026-10-14) and would mis-slice the level-0 data on such textures.
        return w * h * 2
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("core", type=pathlib.Path)
    ap.add_argument("out_dir", type=pathlib.Path)
    ap.add_argument("--min-width", type=int, default=512)
    a = ap.parse_args()
    t0 = time.time()
    a.out_dir.mkdir(parents=True, exist_ok=True)
    env = UnityPy.load(str(a.core))
    before = after = mod = 0
    for x in env.objects:
        if x.type.name != "Texture2D":
            continue
        d = x.read()
        try:
            f = TextureFormat(d.m_TextureFormat).name
        except Exception:
            f = str(d.m_TextureFormat)
        before += d.m_CompleteImageSize
        if d.m_Width >= a.min_width and d.m_MipCount >= 2 and d.m_ImageCount == 1:
            l0 = level0_size(d.m_Width, d.m_Height, f)
            raw = bytes(d.image_data)
            if l0 is not None and l0 < len(raw):
                d.image_data = raw[l0:]
                d.m_Width //= 2
                d.m_Height //= 2
                d.m_MipCount -= 1
                d.m_CompleteImageSize = len(raw) - l0
                d.save()
                mod += 1
                after += d.m_CompleteImageSize
                continue
        after += d.m_CompleteImageSize
    print(f"modified={mod} payload {before/1048576:.1f} -> {after/1048576:.1f} MB")
    env.save(pack="lz4", out_path=str(a.out_dir))
    for f in a.out_dir.iterdir():
        print(f"OUT {f.name} {f.stat().st_size} bytes")
    print(f"done in {time.time()-t0:.0f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())

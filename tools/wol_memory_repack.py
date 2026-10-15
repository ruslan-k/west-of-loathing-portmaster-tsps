#!/usr/bin/env python3
"""WoL memory repack.

Two independent, combinable passes over the owner's UnityFS bundle:

1. mip promotion (default, `--min-width`): promote mip level 1 to level 0 for
   Texture2D assets with m_Width >= 512. The Switch bundle (original
   StreamingAssets/core, 200,367,356 bytes) carries 4411 Texture2D whose
   decompressed payload totals ~1900 MB - more than the TSPS's 963 MiB RAM. Every
   texture stores a full mip chain, so level 1 (a box-filtered half-resolution
   copy) already exists in the bytes: re-slicing the chain and halving
   m_Width/m_Height/m_MipCount shrinks the payload with zero re-encoding.
   Measured: 1450 textures modified, payload 1899.7 -> 603.2 MB. This is the
   currently deployed baseline; its Sprite RenderData corrections are part of it.

2. `--max-mip-levels N`: drop every mip level beyond the first N (N=1 keeps
   only level 0). Dimensions do not change, so Sprite RenderData stays valid:
   the mip tail is only addressing data inside the same texture. Savings are the
   shrink of the remaining chains (~25% of a full chain for N=1, computed per
   texture, block-aligned per level). Only exact-length, single-image,
   non-streamed chains are touched; everything else is reported and skipped.
   `--dry-run` writes no output; `--manifest FILE` records every decision.

The repacked bundle is OWNER DATA: keep inputs/outputs local, never publish
them. The deploy contract (measured): the UnityFS bundle starts at section
offset 0x4DB0D0 (0x78000 romfs offset + 0x4630d0 file offset); the runtime
verifies the section by SIZE only, the guest parses its own RomFS metadata, and
the repacked file may be padded with zeros back to exactly 200,367,356 bytes so
the RomFS file entry stays valid (the deployed baseline uses that padding; a
smaller logical RomFS size is a separate experiment).

Usage: python3 wol_memory_repack.py <core> <out_dir> [--min-width 512]
    [--repair-sprites] [--max-mip-levels 1] [--dry-run] [--manifest FILE]
"""
import argparse
import pathlib
import re
import sys
import time

import UnityPy
from UnityPy.enums import TextureFormat

BLOCK = {"DXT1": 8, "BC4": 8, "DXT5": 16, "BC5": 16, "BC6H": 16, "BC7": 16}


def level0_size(w, h, fmt):
    """Byte size of one mip level with the given dimensions (Unity block rules)."""
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


def mip_chain_size(w, h, fmt, mips):
    """Exact byte size of the first `mips` levels; None for unknown formats."""
    total = 0
    for i in range(mips):
        s = level0_size(max(1, w >> i), max(1, h >> i), fmt)
        if s is None:
            return None
        total += s
    return total


def scale_sprite_pixel_metadata(sprite, scale, *, ui=False):
    """Keep UVs and local geometry invariant when a texture is resized.

    Sprite mesh positions and their normalized UVs are already baked: leave them
    byte-exact. RenderData pixel-space sampling rects and UV affine transforms
    track the texture. Preserve world-sprite logical rect, border and PPU. UGUI
    also derives padding from the logical rect: scale its rect/border/offset/PPU
    together so padding follows the new texture while rect/PPU size is invariant.
    """
    if scale == 1.0:
        return
    if scale != 0.5:
        raise ValueError('only one-level mip promotion is supported')
    if ui:
        # UGUI derives mesh padding from logical rect versus texture rect; both
        # pixel rectangles must use the same units. Rect/PPU preserves UI size.
        for field in ('m_Rect', 'm_Offset', 'm_Border'):
            for key, value in sprite[field].items():
                sprite[field][key] = value * scale
        sprite['m_PixelsToUnits'] *= scale
    rd = sprite['m_RD']
    for field in ('textureRect', 'textureRectOffset', 'uvTransform'):
        for key, value in rd[field].items():
            rd[field][key] = value * scale
    # (-1,-1) is the serialized "not packed" sentinel, not a pixel coordinate.
    for key, value in rd.get('atlasRectOffset', {}).items():
        if value >= 0:
            rd['atlasRectOffset'][key] = value * scale


def is_dynamic_map_ui_sprite(name):
    """Map Image.sprite refs are null in the prefabs and filled by game code.

    Their pixel rect/PPU must follow UI padding rules despite not appearing in
    serialized MonoBehaviour.m_Sprite refs. Do not classify wall/world maps.
    """
    return (name in ('map_bsbg', 'map_blankbg')
            or re.fullmatch(r'mainmapbg\d+(?:_[bc])?', name) is not None
            or name.startswith(('map_icon_', 'mapicon_')))


def should_promote_texture(width, mip_count, image_count, path_id, keep_ids, min_width):
    return (path_id not in keep_ids and width >= min_width
            and mip_count >= 2 and image_count == 1)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("core", type=pathlib.Path)
    ap.add_argument("out_dir", type=pathlib.Path)
    ap.add_argument("--min-width", type=int, default=512)
    ap.add_argument("--repair-sprites", action="store_true",
                    help="experimental: scale dependent sprite pixel metadata too")
    ap.add_argument("--keep-texture-id", type=int, action="append", default=[],
                    help="preserve this owner-bundle texture and its sprite metadata verbatim")
    ap.add_argument("--max-mip-levels", type=int, default=0,
                    help="keep at most N mip levels per texture (1 = level 0 only); 0 disables")
    ap.add_argument("--dry-run", action="store_true",
                    help="report the outcome without writing the bundle")
    ap.add_argument("--manifest", type=pathlib.Path,
                    help="write a TSV of every strip decision")
    a = ap.parse_args()
    keep_ids = set(a.keep_texture_id)
    t0 = time.time()
    if not a.dry_run:
        a.out_dir.mkdir(parents=True, exist_ok=True)
    env = UnityPy.load(str(a.core))
    before = after = mod = 0
    changed_textures = set()
    strip_rows = []
    strip_stripped = strip_skipped = 0
    strip_before = strip_after = 0
    strip_reasons = {}
    for x in env.objects:
        if x.type.name != "Texture2D":
            continue
        d = x.read()
        try:
            f = TextureFormat(d.m_TextureFormat).name
        except Exception:
            f = str(d.m_TextureFormat)
        before += d.m_CompleteImageSize
        dirt = False
        if should_promote_texture(d.m_Width, d.m_MipCount, d.m_ImageCount,
                                  x.path_id, keep_ids, a.min_width):
            l0 = level0_size(d.m_Width, d.m_Height, f)
            raw = bytes(d.image_data)
            if l0 is not None and l0 < len(raw):
                d.image_data = raw[l0:]
                d.m_Width //= 2
                d.m_Height //= 2
                d.m_MipCount -= 1
                d.m_CompleteImageSize = len(raw) - l0
                changed_textures.add((id(x.assets_file), x.path_id))
                mod += 1
                dirt = True
        if a.max_mip_levels > 0 and d.m_MipCount > a.max_mip_levels:
            mips_before = d.m_MipCount
            payload_before = d.m_CompleteImageSize
            raw = bytes(d.image_data)
            keep_size = 0
            reason = None
            if x.path_id in keep_ids:
                reason = "keep-id"
            else:
                keep_size = mip_chain_size(d.m_Width, d.m_Height, f, a.max_mip_levels) or 0
                full = mip_chain_size(d.m_Width, d.m_Height, f, mips_before)
                if d.m_ImageCount != 1:
                    reason = "multi-image"
                elif getattr(d.m_StreamData, "size", 0):
                    reason = "streamed"
                elif not keep_size or full is None:
                    reason = "unknown-format"
                elif len(raw) != full:
                    reason = "length-mismatch"
                elif keep_size >= len(raw):
                    reason = "no-gain"
            if reason is None:
                d.image_data = raw[:keep_size]
                d.m_MipCount = a.max_mip_levels
                d.m_CompleteImageSize = keep_size
                dirt = True
                strip_stripped += 1
                strip_before += payload_before
                strip_after += keep_size
                action = "strip"
            else:
                strip_skipped += 1
                strip_reasons[reason] = strip_reasons.get(reason, 0) + 1
                action = "skip:" + reason
            strip_rows.append((x.path_id, d.m_Name, f, d.m_Width, d.m_Height,
                               mips_before, d.m_MipCount, payload_before,
                               d.m_CompleteImageSize, action))
        if dirt and not a.dry_run:
            d.save()
        after += d.m_CompleteImageSize
    if a.max_mip_levels > 0 and a.manifest:
        header = ("path_id\tname\tformat\twidth\theight\tmips_before\tmips_after"
                  "\tpayload_before\tpayload_after\taction\n")
        lines = [header] + ["\t".join(str(c) for c in r) + "\n" for r in strip_rows]
        a.manifest.write_text("".join(lines))
        print(f"manifest rows={len(strip_rows)} -> {a.manifest}")
    sprites_fixed = 0
    if a.repair_sprites:
        ui_sprites = set()
        for x in env.objects:
            if x.type.name != 'MonoBehaviour':
                continue
            data = x.read_typetree()
            ref = data.get('m_Sprite')
            if ref and ref['m_FileID'] == 0:
                ui_sprites.add((id(x.assets_file), ref['m_PathID']))
        for x in env.objects:
            if x.type.name != 'Sprite':
                continue
            sprite = x.read_typetree()
            ref = sprite['m_RD']['texture']
            if ref['m_FileID'] != 0:
                raise ValueError('external sprite texture reference needs explicit resolution')
            if (id(x.assets_file), ref['m_PathID']) not in changed_textures:
                continue
            ui = ((id(x.assets_file), x.path_id) in ui_sprites
                  or is_dynamic_map_ui_sprite(sprite['m_Name']))
            scale_sprite_pixel_metadata(sprite, 0.5, ui=ui)
            if not a.dry_run:
                x.save_typetree(sprite)
            sprites_fixed += 1
    print(f"modified={mod} sprite_metadata_repaired={sprites_fixed} payload {before/1048576:.1f} -> {after/1048576:.1f} MB")
    if a.max_mip_levels > 0:
        why = " ".join(f"{k}={v}" for k, v in sorted(strip_reasons.items()))
        print(f"mip-strip max_levels={a.max_mip_levels} stripped={strip_stripped} skipped={strip_skipped} "
              f"tail payload {strip_before/1048576:.1f} -> {strip_after/1048576:.1f} MB "
              f"(saved {(strip_before-strip_after)/1048576:.1f} MB) {why}".strip())
    if a.dry_run:
        print("DRY-RUN: nothing written")
        print(f"done in {time.time()-t0:.0f}s")
        return 0
    env.save(pack="lz4", out_path=str(a.out_dir))
    for f in a.out_dir.iterdir():
        print(f"OUT {f.name} {f.stat().st_size} bytes")
    print(f"done in {time.time()-t0:.0f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())

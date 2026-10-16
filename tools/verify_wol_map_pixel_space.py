#!/usr/bin/env python3
"""Verify owner-only map repacks: original pixel space, unchanged unrelated data."""
from pathlib import Path
import argparse
import hashlib
import json
from types import SimpleNamespace

import UnityPy
from UnityPy.enums import TextureFormat
from wol_memory_repack import mip_chain_size, map_pixel_coordinate_texture_ids


def validate_map_texture(original, candidate, max_mip_levels=1):
    """Preserve pixel dimensions and the explicitly requested original mip prefix."""
    if max_mip_levels < 0:
        raise ValueError('negative mip limit')
    fields=('m_Width','m_Height','m_TextureFormat','m_ImageCount')
    if any(getattr(original,k)!=getattr(candidate,k) for k in fields):
        raise ValueError('authored map pixel dimensions or format changed')
    mips=min(original.m_MipCount,max_mip_levels) if max_mip_levels else original.m_MipCount
    if candidate.m_MipCount != mips:
        raise ValueError('map mip count differs from explicit strip contract')
    size=mip_chain_size(original.m_Width,original.m_Height,
                        TextureFormat(original.m_TextureFormat).name,mips)
    if size is None:
        raise ValueError('unsupported protected texture format')
    pixels=bytes(original.image_data)[:size]
    if len(pixels)!=size or bytes(candidate.image_data)!=pixels or candidate.m_CompleteImageSize!=size:
        raise ValueError('map mip prefix is not byte-exact original')


def objects(env):
    result = {}
    for obj in env.objects:
        key = (obj.assets_file.name, obj.path_id)
        if key in result:
            raise ValueError('duplicate object identity')
        result[key] = obj
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('original', 'baseline', 'candidate', 'out'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--max-mip-levels',type=int,default=1,
                        help='expected retained mip cap; 0 preserves the original chain (default: 1)')
    args = parser.parse_args()
    original = objects(UnityPy.load(str(args.original)))
    protected = map_pixel_coordinate_texture_ids(
        obj.read_typetree() for obj in original.values() if obj.type.name == 'Sprite')
    original_textures = {}
    original_sprites = {}
    for key, obj in original.items():
        if obj.type.name == 'Texture2D' and obj.path_id in protected:
            data = obj.read()
            original_textures[key] = SimpleNamespace(
                **{k:getattr(data,k) for k in ('m_Width','m_Height','m_TextureFormat',
                                              'm_ImageCount','m_MipCount')},
                image_data=bytes(data.image_data))
        elif obj.type.name == 'Sprite':
            ref = obj.read_typetree()['m_RD']['texture']
            if ref['m_FileID'] == 0 and ref['m_PathID'] in protected:
                original_sprites[key] = obj.get_raw_data()
    original_keys = set(original)
    del original
    baseline = objects(UnityPy.load(str(args.baseline)))
    candidate = objects(UnityPy.load(str(args.candidate)))
    if baseline.keys() != candidate.keys() or set(candidate) != original_keys:
        raise ValueError('object identities changed')
    changed_textures = changed_sprites = unchanged = payload = baseline_payload = 0
    for key, obj in candidate.items():
        old = baseline[key]
        changed = obj.get_raw_data() != old.get_raw_data()
        if key in original_textures:
            data = obj.read()
            validate_map_texture(original_textures[key],data,args.max_mip_levels)
            changed_textures += changed
        elif key in original_sprites:
            if obj.get_raw_data() != original_sprites[key]:
                raise ValueError(f'map Sprite metadata differs from original: {key}')
            changed_sprites += changed
        elif changed:
            raise ValueError(f'unrelated object changed: {key}')
        if not changed:
            unchanged += 1
        if obj.type.name == 'Texture2D':
            payload += obj.read().m_CompleteImageSize
            baseline_payload += old.read().m_CompleteImageSize
    result = dict(schema=1, status='OFFLINE_VERIFIED', objects=len(candidate),
                  max_mip_levels=args.max_mip_levels,
                  protected_texture_count=len(original_textures),
                  original_sprite_count=len(original_sprites),
                  changed_textures=changed_textures, changed_sprites=changed_sprites,
                  unchanged_objects_byte_exact=unchanged,
                  baseline_payload_bytes=baseline_payload, candidate_payload_bytes=payload,
                  payload_delta_bytes=payload-baseline_payload,
                  candidate_bundle_bytes=args.candidate.stat().st_size,
                  caveat='No device visual, memory or frame-rate claim from this offline check.')
    for name in ('original', 'baseline', 'candidate'):
        with getattr(args, name).open('rb') as handle:
            result[name + '_core_sha256'] = hashlib.file_digest(handle, 'sha256').hexdigest()
    args.out.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()

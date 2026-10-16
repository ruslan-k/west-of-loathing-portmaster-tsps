#!/usr/bin/env python3
"""Which sprites did the repack rescale, and is each one exposed to raw-pixel consumers?

The Android/UI class risk is specific: a consumer that multiplies an authored
pixel-space coordinate by a Sprite rect dimension. Such a consumer is only at
risk for a sprite whose rect/PPU the repacker scaled, so the audit reports the
rescaled sprite set by name class instead of auditing every Sprite caller.
"""
from pathlib import Path
import argparse
import collections
import json
import re

import UnityPy


def sprite_rows(path):
    env = UnityPy.load(str(path))
    objs = {o.path_id: o for o in env.objects}
    rows = {}
    for oid, obj in objs.items():
        if obj.type.name != 'Sprite':
            continue
        s = obj.read_typetree()
        rd = s.get('m_RD') or {}
        ref = rd.get('texture') or {}
        rows[oid] = {
            'name': s.get('m_Name', ''),
            'rect': [s['m_Rect']['x'], s['m_Rect']['y'], s['m_Rect']['width'], s['m_Rect']['height']],
            'ppu': s['m_PixelsToUnits'],
            'texture_rect': [rd['textureRect'][k] for k in ('x', 'y', 'width', 'height')],
            'texture_id': ref.get('m_PathID') if ref.get('m_FileID') == 0 else None,
            'external_texture': bool(ref.get('m_FileID')),
        }
    del env
    return rows


def name_class(name):
    if name.startswith(('map_icon_', 'mapicon_')):
        return 'map icon (protected)'
    if name in ('map_bsbg', 'map_blankbg') or re.fullmatch(r'mainmapbg\d+(?:_[bc])?', name):
        return 'map background (protected)'
    if name.startswith(('map_', 'map')):
        return 'other map_named'
    if name.startswith(('ui_', 'uibg', 'button', 'btn_', 'icon_', 'hud_', 'menu')):
        return 'ui_named'
    if name.startswith(('font', 'text_', 'letter')):
        return 'text_named'
    if name.startswith(('portrait', 'face_', 'char_')):
        return 'character_named'
    return 'other'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--original', type=Path, required=True)
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    original = sprite_rows(args.original)
    candidate = sprite_rows(args.candidate)
    if set(original) != set(candidate):
        raise ValueError('sprite identity set changed')
    rescaled = []
    groups = collections.defaultdict(lambda: collections.Counter())
    samples = collections.defaultdict(list)
    rect_scaled = ppu_scaled = texrect_scaled = unchanged = 0
    for oid, new in candidate.items():
        old = original[oid]
        cls = name_class(new['name'])
        rect_differs = new['rect'] != old['rect']
        ppu_differs = new['ppu'] != old['ppu']
        texrect_differs = new['texture_rect'] != old['texture_rect']
        rect_scaled += rect_differs
        ppu_scaled += ppu_differs
        texrect_scaled += texrect_differs
        if not (rect_differs or ppu_differs or texrect_differs):
            unchanged += 1
            groups[cls]['unchanged'] += 1
            continue
        if rect_differs or ppu_differs:
            rescaled.append({'id': oid, 'name': new['name'], 'class': cls,
                             'rect': old['rect'], 'rect_now': new['rect'],
                             'ppu': [old['ppu'], new['ppu']],
                             'texture_rect': old['texture_rect'],
                             'texture_rect_now': new['texture_rect']})
        groups[cls]['changed'] += 1
        groups[cls]['rect_scaled'] += rect_differs
        groups[cls]['ppu_scaled'] += ppu_differs
        groups[cls]['texture_rect_scaled'] += texrect_differs
        groups[cls]['mixed_units'] += rect_differs != texrect_differs
        if len(samples[cls]) < 16:
            samples[cls].append({'id': oid, 'name': new['name'], 'rect': old['rect'], 'rect_now': new['rect'],
                                 'ppu': [old['ppu'], new['ppu']],
                                 'texture_rect': old['texture_rect'], 'texture_rect_now': new['texture_rect']})
    report = {
        'schema': 1,
        'sprites': len(candidate),
        'rect_scaled': rect_scaled,
        'ppu_scaled': ppu_scaled,
        'texture_rect_scaled': texrect_scaled,
        'untouched': unchanged,
        'by_name_class': {k: dict(v) for k, v in sorted(groups.items())},
        'rescaled_sprites': rescaled,
        'samples': {k: v for k, v in sorted(samples.items())},
        'caveat': ('A sprite being rescaled is not by itself a defect: it matters only when a real '
                   'consumer multiplies an authored pixel-space value by a rect dimension. World '
                   'sprites keep rect/PPU and change only their pixel sampling rectangle.'),
    }
    args.out.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'samples'}, indent=2))


if __name__ == '__main__':
    main()

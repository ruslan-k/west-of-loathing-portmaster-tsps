#!/usr/bin/env python3
"""Select second-level mip-promotion candidates from a repack manifest (M4).

Rules (first wave, 2026-10-15):
* only DXT1/DXT5: the compressed world/background art. 16/32-bit formats are
  UI/font/character pixels and stay untouched.
* current (post-baseline) width and height >= --min (default 1024).
* name must not contain any blocked substring (default list below).

Writes a TSV for `wol_memory_repack.py --levels-file`: `path_id<TAB>1` rows plus
a comment header. The printed list is the review surface; nothing is applied by
this tool.

Usage: wol_m4_select.py MANIFEST.tsv LEVELS.tsv [--min 1024] [--keep ID]...
"""
import argparse
import pathlib
import sys

BLOCKED = ('ui', 'atlas', 'title', 'map', 'mainmap', 'font', 'icon', 'sprite',
           'controller', 'poster', 'sign', 'logo', 'hud', 'menu', 'face',
           'portrait', 'char', 'cursor', 'button', 'panel', 'letter', 'fakebuilding')
SUBSTRINGS = ('poster', 'wanted')


def blocked_by(name, extra=()):
    """Token match: a blocked word must equal a name token or prefix it, so
    'biscuit' does not match 'ui' and 'mainmapbg6' does match 'mainmap'.
    Substring list catches bare compounds like cc_wantedposter."""
    for token in name.lower().split('_'):
        for b in BLOCKED:
            if token == b or token.startswith(b):
                return b
    for b in SUBSTRINGS:
        if b in name.lower():
            return b
    for b in extra:
        if b in name.lower():
            return b
    return None


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('manifest', type=pathlib.Path)
    ap.add_argument('levels', type=pathlib.Path)
    ap.add_argument('--min', type=int, default=1024)
    ap.add_argument('--keep', type=int, action='append', default=[])
    a = ap.parse_args()

    keep = set(a.keep)
    chosen = []
    excluded = []
    for line in a.manifest.read_text().splitlines()[1:]:
        cols = line.split('\t')
        if len(cols) < 10 or cols[9] != 'strip':
            continue
        pid, name, fmt, w, h, pa = int(cols[0]), cols[1], cols[2], int(cols[3]), int(cols[4]), int(cols[8])
        if fmt not in ('DXT1', 'DXT5') or w < a.min or h < a.min:
            continue
        low = name.lower()
        hit = blocked_by(low)
        if hit or pid in keep:
            excluded.append((name, hit or 'keep', pa))
            continue
        chosen.append((pid, name, fmt, w, h, pa))
    chosen.sort(key=lambda c: -c[5])
    total = sum(c[5] for c in chosen)
    saved = sum(c[5] // 4 * 3 for c in chosen)

    rows = ['# M4 second-level promotion: path_id<TAB>extra_steps',
            f'# rules: DXT1/DXT5, w,h>={a.min}, blocked={",".join(BLOCKED)}',
            f'# selected {len(chosen)} textures, payload {total/1048576:.1f} MB, '
            f'expected save {saved/1048576:.1f} MB']
    rows += [f'{c[0]}\t1' for c in chosen]
    a.levels.write_text('\n'.join(rows) + '\n')
    print(f'selected {len(chosen)} textures payload {total/1048576:.1f} MB '
          f'expected_save {saved/1048576:.1f} MB -> {a.levels}')
    print('excluded by rule (name, reason, payload KB):')
    for name, reason, pa in excluded[:25]:
        print(f'  {name[:40]:40} {reason:8} {pa//1024} KB')
    return 0


if __name__ == '__main__':
    sys.exit(main())

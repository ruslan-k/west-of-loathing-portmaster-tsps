#!/usr/bin/env python3
"""Guest/host VMA census for the WoL runtime: where the working set actually lives.

Read-only. Samples /proc/<pid>/smaps (kernel truth: RSS, Swap, Private_Dirty per
mapping) instead of guessing from our own bookkeeping, aggregates by mapping
class, and reports the cold/dirty split that decides whether a mapping is a
candidate for sparse commit or ROMFS read-only mapping.

Device-side usage (no dependencies beyond python3):
    python3 wol_guest_vma_census.py --pid 1234 --out /tmp/census.json
Host-side wrapper collects it during a live run:
    python3 wol_guest_vma_census.py --label rect-d1 --phase gameplay
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

FIELDS = {
    'Size': 'size_kb',
    'Rss': 'rss_kb',
    'Pss': 'pss_kb',
    'Shared_Clean': 'shared_clean_kb',
    'Shared_Dirty': 'shared_dirty_kb',
    'Private_Clean': 'private_clean_kb',
    'Private_Dirty': 'private_dirty_kb',
    'Referenced': 'referenced_kb',
    'Swap': 'swap_kb',
    'SwapPss': 'swap_pss_kb',
    'Anonymous': 'anon_kb',
}


def classify(path: str) -> str:
    p = path.lower()
    if '[heap]' in p:
        return 'heap'
    if '[stack' in p:
        return 'stack'
    if 'wol-romfs' in p or 'romfs' in p:
        return 'romfs'
    if '/dev/dri' in p or 'mali' in p or '/dev/kgsl' in p:
        return 'gpu-driver'
    if 'wol-house' in p:
        return 'house-romfs'
    if p.startswith('/memfd'):
        return 'memfd'
    if p.endswith('.so') or '.so.' in p:
        return 'shared-lib'
    if p.startswith('/') and not p.startswith('[v'):
        return 'file'
    return 'anon'


def parse_smaps(text: str) -> list[dict]:
    regions: list[dict] = []
    cur: dict | None = None
    for line in text.splitlines():
        if line and line[0].isdigit() and '-' in line.split()[0]:
            if cur:
                regions.append(cur)
            parts = line.split()
            start, end = parts[0].split('-')
            cur = {
                'start': int(start, 16),
                'end': int(end, 16),
                'perms': parts[1],
                'name': ' '.join(parts[5:]) if len(parts) > 5 else '',
                'size_kb': 0, 'rss_kb': 0, 'pss_kb': 0,
                'shared_clean_kb': 0, 'shared_dirty_kb': 0,
                'private_clean_kb': 0, 'private_dirty_kb': 0,
                'referenced_kb': 0, 'swap_kb': 0, 'swap_pss_kb': 0, 'anon_kb': 0,
            }
        elif cur and ':' in line:
            key, _, rest = line.partition(':')
            field = FIELDS.get(key.strip())
            if field:
                cur[field] = int(rest.split()[0]) if rest.split() else 0
    if cur:
        regions.append(cur)
    for r in regions:
        r['class'] = classify(r['name'])
    return regions


def census(pid: int) -> dict:
    base = Path(f'/proc/{pid}')
    meminfo = {}
    for line in (Path('/proc/meminfo').read_text().splitlines()):
        k, _, rest = line.partition(':')
        if rest.strip():
            meminfo[k] = int(rest.split()[0])
    status = {}
    for line in (base / 'status').read_text().splitlines():
        k, _, rest = line.partition(':')
        status[k] = rest.strip()
    regions = parse_smaps((base / 'smaps').read_text())
    by_class: dict[str, dict] = {}
    for r in regions:
        c = by_class.setdefault(r['class'], {
            'regions': 0, 'size_kb': 0, 'rss_kb': 0, 'pss_kb': 0,
            'private_dirty_kb': 0, 'private_clean_kb': 0,
            'shared_clean_kb': 0, 'shared_dirty_kb': 0,
            'swap_kb': 0, 'referenced_kb': 0,
        })
        c['regions'] += 1
        for key in ('size_kb', 'rss_kb', 'pss_kb', 'private_dirty_kb', 'private_clean_kb',
                    'shared_clean_kb', 'shared_dirty_kb', 'swap_kb', 'referenced_kb'):
            c[key] += r[key]
    for c in by_class.values():
        size = c['size_kb'] or 1
        c['resident_ratio'] = round((c['rss_kb'] + c['swap_kb']) / size, 4)
        c['dirty_ratio'] = round((c['private_dirty_kb'] + c['shared_dirty_kb']) / size, 4)
    big = sorted(regions, key=lambda r: r['rss_kb'] + r['swap_kb'], reverse=True)[:15]
    return {
        'schema': 1,
        'pid': pid,
        'comm': (base / 'comm').read_text().strip(),
        'captured_at': int(time.time()),
        'smaps_rollup': {
            'rss_kb': sum(r['rss_kb'] for r in regions),
            'pss_kb': sum(r['pss_kb'] for r in regions),
            'swap_kb': sum(r['swap_kb'] for r in regions),
            'private_dirty_kb': sum(r['private_dirty_kb'] for r in regions),
        },
        'by_class': by_class,
        'largest_regions': [
            {k: r[k] for k in ('class', 'name', 'start', 'size_kb', 'rss_kb', 'private_dirty_kb', 'swap_kb', 'perms')}
            for r in big
        ],
        'status': {k: status.get(k) for k in ('VmPeak', 'VmSize', 'VmHWM', 'VmRSS', 'VmSwap', 'Threads')},
        'meminfo': {k: meminfo.get(k) for k in ('MemTotal', 'MemAvailable', 'CmaFree', 'CmaTotal', 'SwapFree', 'SwapTotal')},
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--pid', type=int, help='runtime pid on this machine')
    ap.add_argument('--out', help='write JSON here')
    args = ap.parse_args()
    if not args.pid:
        ap.error('--pid is required for a local census')
    data = census(args.pid)
    text = json.dumps(data, indent=2)
    if args.out:
        Path(args.out).write_text(text + '\n')
        print(args.out)
    else:
        print(text)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

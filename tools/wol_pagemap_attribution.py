#!/usr/bin/env python3
"""Read-only, non-atomic pagemap attribution; aliases are not extra physical RAM.

Resident identities use PFNs; swapped identities use (swap type, swap offset).
Hidden/zero PFNs remain unknown. Owner groups describe VMA classes, not allocator
liveness. Never discard guest pages based on this report.
"""
from __future__ import annotations

import argparse
import json
import os
import struct
import time
from collections import Counter, defaultdict
from pathlib import Path

PAGE = os.sysconf('SC_PAGESIZE')
PRESENT = 1 << 63
SWAPPED = 1 << 62
PFN_MASK = (1 << 55) - 1


def classify(path: str) -> str:
    p = path.lower()
    if '[heap]' in p:
        return 'heap'
    if '[stack' in p:
        return 'stack'
    if 'romfs' in p:
        return 'romfs'
    if '/dev/dri' in p or 'mali' in p:
        return 'gpu-driver'
    if p.startswith('/memfd'):
        return 'memfd'
    if p.endswith('.so') or '.so.' in p:
        return 'shared-lib'
    if p.startswith('/') and not p.startswith('[v'):
        return 'file'
    return 'anon'


def parse_maps(pid: int) -> list[dict]:
    out = []
    for line in Path(f'/proc/{pid}/maps').read_text().splitlines():
        parts = line.split(None, 5)
        start, end = (int(x, 16) for x in parts[0].split('-'))
        name = parts[5] if len(parts) > 5 else ''
        out.append({'start': start, 'end': end, 'name': name, 'class': classify(name)})
    return out


def account_pages(chunks) -> dict:
    """Consume bounded raw pagemap chunks without reading page contents."""
    classes = defaultdict(Counter)
    resident = {}
    swapped = {}
    for owner, raw in chunks:
        if len(raw) % 8:
            raise ValueError('truncated pagemap entries')
        count = classes[owner]
        for (entry,) in struct.iter_unpack('<Q', raw):
            count['mapped_pages'] += 1
            if entry & PRESENT:
                count['present_pages'] += 1
                pfn = entry & PFN_MASK
                if not pfn:
                    count['unknown_pfn_pages'] += 1
                else:
                    resident.setdefault(pfn, set()).add(owner)
            elif entry & SWAPPED:
                count['swapped_pages'] += 1
                key = (entry & 31, (entry & PFN_MASK) >> 5)
                swapped.setdefault(key, set()).add(owner)
            else:
                count['unmapped_pages'] += 1
    fields = ('mapped_pages', 'present_pages', 'swapped_pages',
              'unmapped_pages', 'unknown_pfn_pages')
    totals: dict = {k: sum(c[k] for c in classes.values()) for k in fields}
    available = totals['unknown_pfn_pages'] == 0
    totals.update(known_unique_present_pages=len(resident),
                  unique_present_pages=len(resident) if available else None,
                  resident_repeat_pages=totals['present_pages']-len(resident) if available else None,
                  unique_swap_pages=len(swapped),
                  swap_repeat_pages=totals['swapped_pages']-len(swapped))
    def groups(identities):
        return dict(sorted(Counter('|'.join(sorted(owners)) for owners in identities.values()).items()))
    return dict(totals=totals, resident_dedup_available=available,
                by_class={k: {f: c[f] for f in fields} for k, c in sorted(classes.items())},
                resident_owner_groups=groups(resident), swap_owner_groups=groups(swapped))


def start_ticks(pid):
    return int(Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()[19])


def attribute(pid: int) -> dict:
    begin = time.monotonic_ns()
    boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    identity = start_ticks(pid)
    maps = parse_maps(pid)
    fd = os.open(f'/proc/{pid}/pagemap', os.O_RDONLY)
    def chunks():
        for m in maps:
            first = m['start'] // PAGE
            last = (m['end'] + PAGE - 1) // PAGE
            for at in range(first, last, 4096):
                count = min(4096, last-at)
                raw = os.pread(fd, count*8, at*8)
                if len(raw) != count*8:
                    raise ValueError('short pagemap read')
                yield m['class'], raw
    try:
        result = account_pages(chunks())
    finally:
        os.close(fd)
    if start_ticks(pid) != identity:
        raise RuntimeError('PID identity changed')
    stable = maps == parse_maps(pid)
    totals = result['totals']
    def mib(pages):
        return round(pages*PAGE/1048576, 3) if pages is not None else None
    totals.update(mapped_mb=mib(totals['mapped_pages']),
                  present_mb=mib(totals['present_pages']),
                  unique_physical_mb=mib(totals['unique_present_pages']),
                  shared_repeat_mb=mib(totals['resident_repeat_pages']),
                  unique_pfns=totals['unique_present_pages'],
                  unique_swap_mb=mib(totals['unique_swap_pages']))
    for owner, counts in result['by_class'].items():
        counts.update(mappings=sum(m['class'] == owner for m in maps),
                      present_mb=mib(counts['present_pages']),
                      swapped_mb=mib(counts['swapped_pages']))
    mem = {l.split(':')[0]: int(l.split()[1]) for l in Path('/proc/meminfo').read_text().splitlines()
           if l.split(':')[0] in ('MemAvailable', 'CmaFree', 'SwapFree')}
    result.update(schema=2, pid=pid, start_ticks=identity, boot=boot,
                  comm=Path(f'/proc/{pid}/comm').read_text().strip(),
                  page_kb=PAGE//1024, maps_unchanged=stable, meminfo=mem,
                  t_begin_ns=begin, t_end_ns=time.monotonic_ns(),
                  caveat='Non-atomic metadata scan; PFNs/slots can change during collection. VMA owner classes do not prove allocator liveness. Resident and swapped pages are separate; GPU/PSS/CMA may overlap. *_mb fields are MiB.')
    return result


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--pid', type=int, required=True)
    ap.add_argument('--out')
    a = ap.parse_args()
    data = attribute(a.pid)
    text = json.dumps(data, indent=2)
    if a.out:
        with Path(a.out).open('x') as f:
            f.write(text + '\n')
    print(text)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

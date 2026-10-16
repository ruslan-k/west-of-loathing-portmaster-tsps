#!/usr/bin/env python3
"""Read-only WoL memory/descriptor profiler. Never reads texture/guest payloads.

Pagemap present/swapped/unmapped is NOT allocator live/free information.
Borrowed pool spans alias guest pages and must not be added to PSS.
"""
from pathlib import Path
import hashlib
import json
import os
import re
import struct
import time


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda: f.read(1048576), b''):
            h.update(b)
    return h.hexdigest()


def require_elf(layout, digest):
    if layout['elf_sha256'] != digest:
        raise ValueError('descriptor layout does not match the exact running ELF')


def kv(text):
    result = {}
    for line in text.splitlines():
        parts = line.replace(':', ' ').split()
        if len(parts) > 1 and parts[1].isdigit():
            result[parts[0]] = int(parts[1])
    return result


def parse_smaps(text):
    rows = []
    for line in text.splitlines():
        if re.match(r'^[0-9a-f]+-[0-9a-f]+ ', line):
            p = line.split(None, 5)
            lo, hi = [int(x, 16) for x in p[0].split('-')]
            rows.append(dict(start=lo, end=hi, perms=p[1],
                             path=p[5] if len(p) == 6 else '[anonymous]'))
        elif rows:
            rows[-1].update(kv(line))
    return rows


def merged_ranges(ranges):
    out = []
    for lo, hi in sorted(ranges):
        if hi <= lo:
            continue
        if out and lo <= out[-1][1]:
            out[-1][1] = max(hi, out[-1][1])
        else:
            out.append([lo, hi])
    return out


def union_size(ranges):
    return sum(hi - lo for lo, hi in merged_ranges(ranges))


def page_counts(raw):
    if len(raw) % 8:
        raise ValueError('truncated pagemap')
    out = dict(present=0, swapped=0, unmapped=0, soft_dirty=0)
    for (entry,) in struct.iter_unpack('<Q', raw):
        key = 'present' if entry & (1 << 63) else 'swapped' if entry & (1 << 62) else 'unmapped'
        out[key] += 1
        out['soft_dirty'] += bool(entry & (1 << 55))
    return out


def stat_identity(proc):
    parts = (proc / 'stat').read_text().rsplit(')', 1)[1].split()
    return dict(start_ticks=int(parts[19]), cpu_ticks=int(parts[11]) + int(parts[12]),
                majflt=int(parts[9]), minflt=int(parts[7]))


def lifecycle(before, after):
    a = {r['id'] for r in before.get('textures', [])}
    b = {r['id'] for r in after.get('textures', [])}
    def pools(d):
        return {(r['object'], r['address'], r['size']) for r in d.get('pools', []) if r['live']}
    return dict(created_texture_ids=sorted(b - a), finalized_texture_ids=sorted(a - b),
                new_pool_spans=sorted(pools(after) - pools(before)),
                retired_pool_spans=sorted(pools(before) - pools(after)),
                caveat='Endpoint differences; creation+finalization between snapshots is not observable.')


def platform_state():
    def text(path):
        try:
            return path.read_text().strip()
        except OSError:
            return None
    paths=list(Path('/sys/devices/system/cpu/cpufreq').glob('policy*/*freq'))
    paths+=list(Path('/sys/class/devfreq').glob('*/*freq'))
    return dict(online_cpus=text(Path('/sys/devices/system/cpu/online')),
        clocks={str(p):text(p) for p in paths if p.name in
            ('scaling_min_freq','scaling_max_freq','scaling_cur_freq','cpuinfo_cur_freq','min_freq','max_freq','cur_freq')},
        caveat='Instantaneous observations, not sustained clocks or utilization.')


class Observer:
    def __init__(self, pid, layout=None):
        self.proc = Path('/proc') / str(pid)
        self.pid = pid
        self.identity = stat_identity(self.proc)['start_ticks']
        self.layout = layout
        self.elf_sha256 = sha256(self.proc / 'exe')
        if layout:
            require_elf(layout, self.elf_sha256)
        self.page_size = os.sysconf('SC_PAGE_SIZE')

    def check(self):
        if stat_identity(self.proc)['start_ticks'] != self.identity:
            raise RuntimeError('PID identity changed')

    def sample(self) -> dict:
        self.check()
        def text(p):
            try:
                return p.read_text()
            except OSError:
                return ''
        return dict(t=time.monotonic(), process=stat_identity(self.proc),
                    status=kv(text(self.proc / 'status')),
                    rollup=kv(text(self.proc / 'smaps_rollup')),
                    meminfo=kv(text(Path('/proc/meminfo'))),
                    vmstat=kv(text(Path('/proc/vmstat'))),
                    pressure_memory=text(Path('/proc/pressure/memory')))

    def descriptors(self) -> dict:
        if not self.layout:
            return dict(unavailable='No exact ELF layout supplied', textures=[], pools=[], regions=[])
        l = self.layout
        maps = (self.proc / 'maps').read_text().splitlines()
        exe = os.readlink(self.proc / 'exe')
        base = next(int(p[0].split('-')[0], 16) - int(p[2], 16)
                    for line in maps if len(p := line.split(None, 5)) == 6
                    and p[5] == exe and int(p[2], 16) == 0)
        fd = os.open(self.proc / 'mem', os.O_RDONLY)
        def read(addr, size):
            raw = os.pread(fd, size, addr)
            if len(raw) != size:
                raise RuntimeError('short descriptor read')
            return raw
        def sym(name):
            s = l['symbols'][name]
            return int.from_bytes(read(base + s['offset'], s['size']), 'little')
        def rows(kind, symbol, count):
            size = l[kind + '_size']
            addr = base + l['symbols'][symbol]['offset']
            raw = read(addr, size * count)
            out = []
            for i in range(count):
                b = raw[i * size:(i + 1) * size]
                r = {k: int.from_bytes(b[o:o+s], 'little') for k, (o, s) in l[kind].items()}
                r['slot'] = i
                # Unlocked best effort: ignore torn/reused descriptors.
                keys = ('id', 'object', 'live') if kind == 'texture' else tuple(l[kind])
                b2 = read(addr + i * size, size)
                if any(int.from_bytes(b2[l[kind][k][0]:sum(l[kind][k])], 'little') != r[k] for k in keys):
                    continue
                out.append(r)
            return out
        try:
            high = sym('nvn_textures_high')
            if not 0 <= high <= l['symbols']['nvn_textures']['size'] // l['texture_size']:
                raise RuntimeError('texture table count out of bounds')
            textures = [r for r in rows('texture', 'nvn_textures', high) if r['live']]
            pools = [r for r in rows('pool', 'nvn_pools', 256) if r['live'] or r['references']]
            count = sym('nregions')
            if count > l['symbols']['regions']['size'] // l['region_size']:
                raise RuntimeError('region table count out of bounds')
            regions = rows('region', 'regions', count)
            heap_size = sym('heap_size')
        finally:
            os.close(fd)
        unique = {}
        for t in textures:
            key = ('texture', t['name']) if t['name'] else ('depth', t['depth_buffer'])
            if key[1]:
                unique.setdefault(key, t)
        def extent(t):
            if t['zero_backend_deferred']:
                return 0
            w, h = (t['host_width'], t['host_height']) if t['host_scaled'] else (t['b.width'], t['b.height'])
            f = t['b.format']
            bpp = 2 if t['host_upload_type'] in (0x8033, 0x8034) else 8 if f in (5, 0x11, 0x29) else 16 if f in (0xa, 0x16, 0x2e, 0x12, 0x2a) else 4
            return sum(max(1, w >> i) * max(1, h >> i) * bpp for i in range(t['b.levels'])) * (6 if t['b.target'] == 8 else 1)
        pool_ranges = [(r['address'], r['address'] + r['size']) for r in pools]
        return dict(textures=textures, pools=pools, regions=regions, heap_virtual_bytes=heap_size,
                    texture_objects=len(textures), unique_host_resources=len(unique),
                    host_image_extent_estimate_bytes=sum(extent(t) for t in unique.values()),
                    pool_union_virtual_bytes=union_size(pool_ranges),
                    borrowed_pool_virtual_bytes=union_size([(r['address'], r['address'] + r['size']) for r in pools if not r['owned']]))

    def snapshot(self, phase, pages=True) -> dict:
        self.check()
        result = self.sample()
        result.update(schema=1, phase=phase, pid=self.pid, start_ticks=self.identity,
                      elf_sha256=self.elf_sha256, page_bytes=self.page_size, platform=platform_state())
        result['mappings'] = parse_smaps((self.proc / 'smaps').read_text())
        result['descriptors'] = d = self.descriptors()
        result['pagemap'] = dict(available=False)
        if pages:
            try:
                fd = os.open(self.proc / 'pagemap', os.O_RDONLY)
                try:
                    spans = [('guest_heap', 0x1000000000, 0x1000000000 + d.get('heap_virtual_bytes', 0))]
                    spans += [('pool_union', lo, hi) for lo, hi in merged_ranges([(r['address'], r['address'] + r['size']) for r in d['pools']])]
                    counters = {}
                    for name, lo, hi in spans:
                        if hi <= lo:
                            continue
                        n = (hi - lo + self.page_size - 1) // self.page_size
                        raw = os.pread(fd, n * 8, lo // self.page_size * 8)
                        if len(raw) != n * 8:
                            raise RuntimeError('short pagemap read')
                        c = page_counts(raw)
                        dst = counters.setdefault(name, dict(present=0, swapped=0, unmapped=0, soft_dirty=0))
                        for k, v in c.items():
                            dst[k] += v
                    result['pagemap'] = dict(available=True, counts=counters,
                        caveat='Pool union aliases the heap; do not add. Unmapped/swapped/soft-dirty never proves allocator free pages.')
                finally:
                    os.close(fd)
            except (OSError, RuntimeError) as e:
                result['pagemap'] = dict(available=False, error=str(e))
        result['caveats'] = ['Status and smaps are independent observations and are not reconciled.',
            'No guest payload, texture pixels, allocator free lists, or PFNs were read.',
            'No madvise, decommit, GC or asset unload. Allocator active/free bytes remain unknown.',
            'Host image extents are estimates, not measured Mali allocations, and cannot be added to PSS.']
        self.check()
        return result

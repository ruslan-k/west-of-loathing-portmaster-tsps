#!/usr/bin/env python3
"""Read-only, bounded same-window Mali/VM ledger. No aggregate 'total RAM' sum.

All counters in each row are read between t_begin_ns/t_end_ns, not atomically.
PSS, borrowed pools, Mali commit and CMA can overlap and MUST NOT be added.
"""
import argparse
import json
import math
import re
import time
from pathlib import Path
from wol_memory_profile import Observer, platform_state, stat_identity


def coherent(before, after):
    if before['start_ticks'] != after['start_ticks']:
        raise RuntimeError('PID reused while sampling')


def parse_mali(text):
    rows = re.findall(r'^\s*([0-9a-fA-F]+),\s*([0-9a-fA-F]+),\s*([0-9a-fA-F]+),\s*([0-9a-fA-F]+),', text, re.M)
    return dict(allocations=len(rows), virtual_bytes=sum(int(r[1], 16) for r in rows),
                commit_bytes=sum(int(r[2], 16) for r in rows))


def mali_contexts(root, pid):
    contexts = []
    errors = []
    for p in sorted(Path(root).glob(str(pid)+'_*')):
        if not re.fullmatch(str(pid)+r'_\d+', p.name):
            continue
        try:
            text = (p/'mem_allocs').read_text()
            if not text.startswith('Zone name:') and not parse_mali(text)['allocations']:
                raise ValueError('unrecognized mem_allocs format')
            item=dict(context=p.name, **parse_mali(text))
            sizes=re.findall(r'^\s*[0-9a-fA-F]+,\s*[0-9a-fA-F]+,\s*([0-9a-fA-F]+),',text,re.M)
            item['commit_histogram']={}
            for size in sizes:
                key=str(int(size,16))
                item['commit_histogram'][key]=item['commit_histogram'].get(key,0)+1
            contexts.append(item)
        except (OSError, ValueError) as e:
            errors.append(str(e))
    available = bool(contexts) and not errors
    return dict(available=available, contexts=contexts, errors=errors,
                commit_bytes=sum(c['commit_bytes'] for c in contexts) if available else None,
                caveat='Driver context commits; may overlap PSS/CMA and are not extra RAM.')


def percentile(values, q):
    a = sorted(values)
    x = (len(a)-1)*q
    lo = math.floor(x)
    return a[lo]+(a[math.ceil(x)]-a[lo])*(x-lo)


def frame_stats(text):
    rows = [tuple(map(int, r)) for r in re.findall(r'MOMO_FRAME frame=(\d+) ns=(\d+)', text)]
    if len(rows) < 2:
        return dict(available=False, frames=len(rows))
    if any(b[0] != a[0]+1 or b[1] <= a[1] for a, b in zip(rows, rows[1:])):
        raise ValueError('non-consecutive frame IDs or timestamps; no valid full-interval FPS')
    dt = [(b[1]-a[1])/1e6 for a, b in zip(rows, rows[1:])]
    return dict(available=True, first_frame=rows[0][0], last_frame=rows[-1][0],
                intervals=len(dt), seconds=(rows[-1][1]-rows[0][1])/1e9,
                presents_per_s=len(dt)*1e9/(rows[-1][1]-rows[0][1]),
                p50_ms=percentile(dt, .5), p95_ms=percentile(dt, .95),
                p99_ms=percentile(dt, .99), max_ms=max(dt),
                caveat='Runtime presents, not independent physical panel FPS.')


def sample(observer, phase, layout_pages=False):
    begin = time.monotonic_ns()
    before = stat_identity(observer.proc)
    r = observer.sample()
    r.update(phase=phase, pid=observer.pid, start_ticks=observer.identity,
             mali=mali_contexts(Path('/sys/kernel/debug/mali0/ctx'), observer.pid),
             platform=platform_state())
    if layout_pages:
        snap = observer.snapshot(phase, pages=True)
        d = snap['descriptors']
        r['guest'] = dict(heap_virtual_bytes=d.get('heap_virtual_bytes'),
                          borrowed_pool_virtual_bytes=d.get('borrowed_pool_virtual_bytes'),
                          pool_union_virtual_bytes=d.get('pool_union_virtual_bytes'),
                          pagemap=snap['pagemap'],
                          caveat='Pool/heap spans overlap; present/swapped do not mean active/free.')
    coherent(before, stat_identity(observer.proc))
    r.update(t_begin_ns=begin, t_end_ns=time.monotonic_ns())
    return r


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--pid', type=int, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--seconds', type=float, default=60)
    p.add_argument('--period', type=float, default=2)
    p.add_argument('--layout', type=Path)
    p.add_argument('--phase', default='unclassified')
    p.add_argument('--phase-file', type=Path)
    args = p.parse_args()
    if not (0 < args.seconds <= 7200 and .5 <= args.period <= 60):
        p.error('duration 0..7200, period .5..60 seconds required')
    layout = json.loads(args.layout.read_text()) if args.layout else None
    ob = Observer(args.pid, layout)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    end = time.monotonic()+args.seconds
    count = 0
    with args.out.open('x') as f:
        f.write(json.dumps(dict(schema=1, type='header', elf_sha256=ob.elf_sha256,
            pid=args.pid, start_ticks=ob.identity, period_s=args.period,
            caveat='No payload bytes, no VM mutation; fields overlap, no summed physical total.'))+'\n')
        while time.monotonic() < end:
            t = time.monotonic()
            phase = args.phase
            if args.phase_file and args.phase_file.exists():
                phase = args.phase_file.read_text().strip()[:100]
            try:
                r = sample(ob, phase, layout_pages=bool(layout) and count % 5 == 0)
            except (OSError, RuntimeError) as e:
                f.write(json.dumps(dict(type='end', reason=str(e), samples=count))+'\n')
                break
            f.write(json.dumps(r, separators=(',', ':'))+'\n')
            f.flush()
            count += 1
            time.sleep(max(0, min(end-time.monotonic(), args.period-(time.monotonic()-t))))
    print('LEDGER_DONE', count, args.out, flush=True)


if __name__ == '__main__':
    main()

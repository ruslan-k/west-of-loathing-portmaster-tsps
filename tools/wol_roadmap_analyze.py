#!/usr/bin/env python3
"""Summarize saved owner-device roadmap probes; never combine overlapping RAM fields.

Usage: wol_roadmap_analyze.py RUN_DIR [RUN_DIR ...] --out SUMMARY.json
Requested action labels are NOT scene classifications. Keep the KMS review alongside.
"""
import argparse
from collections import Counter, defaultdict
import gzip
import json
import re
import statistics
from pathlib import Path
from typing import Any
from wol_memory_ledger import frame_stats, percentile


def records(text, prefix):
    return [dict(re.findall(r'([\w-]+)=([^\s]+)', line))
            for line in text.splitlines() if line.startswith(prefix)]


def distribution(values):
    values = [v for v in values if v is not None]
    if not values:
        return dict(available=False)
    return dict(available=True, count=len(values), minimum=min(values),
                median=statistics.median(values), p95=percentile(values, .95), maximum=max(values))


def allocation_ledger(text) -> dict[str, Any]:
    """Join read spans at event time; SDK extents are not Unity object ownership."""
    live={};events=[];reads=[];pools=[];incomplete=False
    for line in text.splitlines():
        if not line.startswith(('WOL_ALLOC ', 'WOL_ROMFS_BUFFER ', 'NVN_MEMORY_POOL_BOUND ')):
            continue
        r=dict(re.findall(r'([\w-]+)=([^\s]+)',line))
        r['parents']=re.findall(r'parent=([^\s]+)',line)
        if line.startswith('WOL_ALLOC '):
            incomplete |= int(r.get('incomplete','0'),0)!=0
            events.append(r)
            ptr=int(r['ptr'],0)
            if r['event']=='free':
                old=live.pop(ptr,None)
                r['matched']=old is not None and old['bytes']==r['bytes']
                if not r['matched']:incomplete=True
            elif r['event'] in ('alloc','realloc'):
                if ptr in live:incomplete=True
                live[ptr]=r
        else:
            address=int(r['address'],0);size=int(r.get('bytes',r.get('size','0')),0)
            r['containing_at_event']=[x for p,x in live.items() if p<=address and size<=p+int(x['bytes'],0)-address]
            (reads if line.startswith('WOL_ROMFS_BUFFER ') else pools).append(r)
    # Allocation event identity, not just a reusable numerical pointer.
    owners={id(x) for pool in pools for x in pool['containing_at_event']}
    total=sum(int(x['bytes'],0) for x in live.values())
    pool_total=sum(int(x['bytes'],0) for x in live.values() if id(x) in owners)
    return dict(events=events,live=list(live.values()),romfs_reads=reads,pool_bindings=pools,
                trace_incomplete=incomplete, SDK_requested_live_bytes=total,
                SDK_requested_ever_pool_bound_live_bytes=pool_total,
                SDK_requested_no_observed_pool_binding_live_bytes=total-pool_total,
                active_Unity_bytes=None, Unity_free_list_bytes=None, safe_reclaimable_bytes=None,
                caveat='Endpoint SDK extents, not physical pages; ever pool-bound is not proof of current pool liveness. No free/reclaim safety is inferred.')


def summarize(root):
    receipt = json.loads((root/'receipt.json').read_text())
    rows = [json.loads(line) for line in (root/'ledger.jsonl').read_text().splitlines()]
    rows = [r for r in rows if 't_begin_ns' in r]
    text = gzip.decompress((root/'runtime.log.gz').read_bytes()).decode(errors='replace')
    frames = [(int(a), int(b)) for a, b in re.findall(r'MOMO_FRAME frame=(\d+) ns=(\d+)', text)]
    phases = defaultdict(list)
    for r in rows:
        phases[r['phase']].append(r)
    stages = receipt['stages']
    bounds = {s['name']: (s['t_ns'], stages[i+1]['t_ns'] if i+1 < len(stages)
                         else max((r['t_end_ns'] for r in rows), default=s['t_ns']))
              for i, s in enumerate(stages)}
    result = dict(label=receipt['label'], runtime_sha256=receipt['runtime_sha256'],
                  section_sha256=receipt['section_sha256'], control_save_hashes=receipt['control_save_hashes'],
                  cleanup_verified=receipt['cleanup_verified'], cleanup_warnings=receipt.get('cleanup_warnings', []),
                  effective_env=json.loads((root/'effective-env.json').read_text()), phases={})
    for phase, samples in phases.items():
        lo, hi = bounds[phase]
        # Fixed two-second action/warmup exclusion. Remaining short windows stay descriptive.
        selected = [(i, t) for i, t in frames if lo+2_000_000_000 <= t < hi]
        item = dict(samples=len(samples), requested_phase=phase, scene_independently_verified=False,
                    window_begin_ns=lo, window_end_ns=hi,
                    pss_kib=distribution(r['rollup'].get('Pss') for r in samples),
                    swap_pss_kib=distribution(r['rollup'].get('SwapPss') for r in samples),
                    vm_swap_kib=distribution(r['status'].get('VmSwap') for r in samples),
                    mem_available_kib=distribution(r['meminfo'].get('MemAvailable') for r in samples),
                    cma_free_kib=distribution(r['meminfo'].get('CmaFree') for r in samples),
                    mali_commit_bytes=distribution(r['mali']['commit_bytes'] for r in samples),
                    sampler_ms=distribution((r['t_end_ns']-r['t_begin_ns'])/1e6 for r in samples),
                    frame_window=frame_stats('\n'.join(f'MOMO_FRAME frame={i} ns={t}' for i,t in selected)))
        if len(samples) > 1:
            item['major_fault_delta'] = samples[-1]['process']['majflt']-samples[0]['process']['majflt']
            item['swapin_pages_delta'] = samples[-1]['vmstat'].get('pswpin',0)-samples[0]['vmstat'].get('pswpin',0)
            item['swapout_pages_delta'] = samples[-1]['vmstat'].get('pswpout',0)-samples[0]['vmstat'].get('pswpout',0)
        result['phases'][phase] = item
    hits = records(text, 'WOL_ASTC_POSTCOPY_HIT ')
    writes = records(text, 'WOL_BC_WRITE ')
    result['astc_postcopy_hits'] = hits
    result['astc_fallbacks'] = records(text, 'ASTC_CACHE_FALLBACK ')
    result['bc_write_census'] = dict(total=len(writes), full=sum(x.get('full')=='1' for x in writes),
                                    by_path=dict(Counter(x['path'] for x in writes)),
                                    by_id=dict(Counter(x['id'] for x in writes)))
    result['copy_audits'] = records(text, 'WOL_COPY_AUDIT ')
    if 'WOL_ALLOC event=' in text:
        result['allocation_ledger'] = allocation_ledger(text)
    result['gl_errors'] = [line for line in text.splitlines()
                           if 'GL_ERROR' in line or 'WOL_ASTC_POSTCOPY_GL_FAIL' in line]
    result['stop_records'] = [line for line in text.splitlines() if line.startswith('STOP ')]
    result['caveats'] = ['PSS, SwapPSS, NVN pools, Mali commit and CMA overlap: no physical total is computed.',
                         'Lightweight sampler runs are memory/performance observations, not sampler-off FPS controls.',
                         'Runtime presents are not independent panel refresh measurements.',
                         'No no-swap or battle/transition coverage is inferred from action labels.']
    return result


def compare(runs):
    arms = defaultdict(list)
    for r in runs:
        variant = 'postcopy' if r['effective_env'].get('WOL_ASTC_POSTCOPY')=='1' else 'control'
        arms[variant].append(r)
    out: dict[str, Any] = dict(arm_counts={k:len(v) for k,v in arms.items()}, per_phase={})
    if not all(k in arms for k in ('control','postcopy')):
        return out
    identities = {(r['runtime_sha256'], r['section_sha256'], json.dumps(r['control_save_hashes'],sort_keys=True)) for r in runs}
    if len(identities)!=1:
        out['matched_identity']=False
        return out
    out['matched_identity']=True
    treatment={'WOL_ASTC_POSTCOPY','WOL_ASTC_POSTCOPY_ID','WOL_ASTC_CACHE','COTM_RUN_ID'}
    environments={json.dumps({k:v for k,v in r['effective_env'].items() if k not in treatment},sort_keys=True) for r in runs}
    out['matched_other_env']=len(environments)==1
    if not out['matched_other_env']:
        return out
    for phase in sorted(set.intersection(*(set(r['phases']) for r in runs))):
        d={}
        for field in ('mali_commit_bytes','pss_kib','swap_pss_kib'):
            a={k:[r['phases'][phase][field].get('median') for r in arms[k]] for k in arms}
            if all(all(x is not None for x in a[k]) for k in a):
                d[field] = dict(control_run_medians=a['control'], postcopy_run_medians=a['postcopy'],
                               median_of_runs_delta=statistics.median(a['postcopy'])-statistics.median(a['control']))
        out['per_phase'][phase]=d
    return out


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('runs',type=Path,nargs='+')
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    runs=[summarize(r) for r in a.runs]
    result=dict(runs=runs,comparison=compare(runs))
    a.out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(runs=len(runs),cleanups=sum(r['cleanup_verified'] for r in runs),
                          gl_errors=sum(len(r['gl_errors']) for r in runs),out=str(a.out))))


if __name__=='__main__':
    main()

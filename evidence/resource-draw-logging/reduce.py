#!/usr/bin/env python3
"""Recompute the four draw-trace A/B windows from stored proc JSON + raw logs."""
from collections import Counter
import json
import lzma
from pathlib import Path
import re
import statistics as st
import sys

root=Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parent
labels=('trace-on-a1','trace-off-b1','trace-on-a2','trace-off-b2')
runs=[]
for label in labels:
    p=root/(label+'-profile.json')
    d=json.loads(p.read_text())
    raw=root/(label+'-profile.runtime-interval.log')
    lines=(raw.read_text() if raw.exists() else lzma.decompress(Path(str(raw)+'.xz').read_bytes()).decode()).splitlines()
    clock=[tuple(map(int,m.groups())) for line in lines if (m:=re.fullmatch(r'MOMO_FRAME frame=(\d+) ns=(\d+)',line))]
    assert len(clock)>300,(label,'not enough frame timestamps')
    assert all(b[0]==a[0]+1 and b[1]>a[1] for a,b in zip(clock,clock[1:])),(label,'discontinuous frame clock')
    periods=[(b[1]-a[1])/1e6 for a,b in zip(clock,clock[1:])]
    prefixes=Counter(line.split()[0] for line in lines if line.strip())
    nonzero=[line for line in lines if (m:=re.search(r'glerror=0x([0-9a-fA-F]+)',line)) and int(m[1],16)]
    assert not nonzero,(label,nonzero[:3])
    s=d['summary'];samples=d['samples'];seconds=s['seconds'];n=len(clock)
    assert 30<=seconds<=32,(label,seconds)
    trace=int(label.startswith('trace-on-'))
    for prefix in ('WOL_CAT_DRAW','WOL_PAIR_BANK','WOL_PAIR_TEX','WOL_PAIR_DRAW','WOL_PROGRAM_BOUND','WOL_PAIR_DRAW_ISSUED','WOL_DOWNSAMPLE_BLIT'):
        assert (prefixes[prefix]>0)==bool(trace),(label,prefix,prefixes[prefix])
    boundary_counts={}
    for prefix in ('NVN_PRESENT_PIXELS','T2P_SLOW_FRAME'):
        ids=[int(m[1]) for line in lines if (m:=re.match(re.escape(prefix)+r' frame=(\d+) ',line))]
        # A bounded byte slice may end after MOMO_FRAME but before that frame's
        # readback/slow-frame receipt. Allow only the one documented edge frame.
        assert ids and all(b==a+1 for a,b in zip(ids,ids[1:])),(label,prefix,'internal receipt gap')
        assert abs(len(ids)-n)<=1,(label,prefix,len(ids),n)
        assert set(ids)^set(x[0] for x in clock)<={clock[0][0]-1,clock[0][0],clock[-1][0],clock[-1][0]+1},(label,prefix,'non-boundary mismatch')
        boundary_counts[prefix]=len(ids)-n
    runs.append(dict(label=label,trace=trace,pid=d['pid'],seconds=seconds,frames=n,boundary_receipt_count_deltas=boundary_counts,
        presents_per_s=1000/st.mean(periods),median_period_ms=st.median(periods),
        p95_period_ms=sorted(periods)[int(.95*(len(periods)-1))],
        log_KiB_per_s=s['log_bytes_per_s']/1024,
        process_cpu_percent=s['cpu_percent'],process_cpu_ms_per_frame=s['cpu_percent']/100*seconds/n*1000,
        rss_mean_MiB=st.mean(x['status']['VmRSS'] for x in samples)/1024,
        swap_mean_MiB=st.mean(x['status']['VmSwap'] for x in samples)/1024,
        process_major_faults_per_s=s['major_faults_per_s'],
        nonzero_gl_errors=len(nonzero),interval_lines=len(lines),prefix_counts=dict(prefixes)))
assert len(runs)==4
means={name:{field:st.mean(x[field] for x in runs if x['trace']==mode) for field in
    ('presents_per_s','log_KiB_per_s','process_cpu_percent','process_cpu_ms_per_frame','rss_mean_MiB','swap_mean_MiB')}
    for name,mode in [('trace_on',1),('trace_off',0)]}
a,b=means['trace_on'],means['trace_off']
result=dict(run_count=len(runs),scene='Stationary Boring Springs, outside Alice office',order=list(labels),
    cpu_percent_convention='100 percent = one logical CPU',
    frame_clock='MOMO_FRAME nanosecond deltas; p95 sorted[int(.95*(n-1))]',
    cpu_per_frame='proc utime+stime / CLK_TCK / frame-record count in the same bounded window',
    runtime_sha256='c35548fb7e56e6d4edb03523ab579fdce1577ffaa3b8cd2b68df32b7d99ecb5b',
    runs=runs,means=means,deltas=dict(log_rate_reduction_percent=100*(1-b['log_KiB_per_s']/a['log_KiB_per_s']),
    cpu_per_frame_reduction_percent=100*(1-b['process_cpu_ms_per_frame']/a['process_cpu_ms_per_frame']),
    presents_per_s_increase_percent=100*(b['presents_per_s']/a['presents_per_s']-1)),
    caveats=['Exploratory A/B/A/B, two 30-second windows per mode; no confidence interval.',
    'Animated scene, varying cache/swap pressure; not a pixel-identical or energy benchmark.',
    'Overall CPU utilization remains similar; no claimed RAM, battery-life or watts saving.',
    'Original gfx265 baseline has different instrumentation and is not the comparator.',
    'Full-frame present readbacks are unchanged and still occur every frame.'])
print(json.dumps(result,indent=2))

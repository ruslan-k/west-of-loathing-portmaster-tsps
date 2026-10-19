#!/usr/bin/env python3
"""Summarize the frozen 720p acceptance trials (roadmap §16.3).

Frame timestamps, stage timestamps and input receipts are all device-monotonic. Requested
stage names are not scene proof: each walk capture is classified against the trial's own
map/world reference frames (numpy luma diff + darkness + static check), and moving stats are
reported over the actual 2 s hold windows restricted to clean world windows. KMS review of
key frames stays a separate manual step; this tool assigns provisional classes for numbers.
"""
from pathlib import Path
import argparse
import gzip
import json
import re
import statistics

import numpy as np
from PIL import Image

from wol_memory_ledger import percentile

PAIRS=(('accept-a1','accept-b1'),('accept-b2','accept-a2'),('accept-a3','accept-b3'))
LUMA_THRESHOLD=20
WORLD_MARGIN=40000
MAP_MARGIN=40000
STATIC_MARGIN=15000
DARK_FRACTION=0.85


def _luma(path):
    with Image.open(path) as im:
        return np.asarray(im.convert('L'),dtype=np.int16)


def shot_diff(a,b):
    la,lb=_luma(a),_luma(b)
    if la.shape!=lb.shape:return None
    return int((np.abs(la-lb)>LUMA_THRESHOLD).sum())


def dark_fraction(path):
    l=_luma(path)
    return float((l<30).mean())


def classify_shot(capture,map_ref,world_ref,prev=None):
    md=shot_diff(capture,map_ref);wd=shot_diff(capture,world_ref)
    dark=dark_fraction(capture)
    pd=shot_diff(capture,prev) if prev else None
    if dark>DARK_FRACTION:cls='transition-dark'
    elif md is not None and wd is not None and wd+WORLD_MARGIN<md:cls='world'
    elif md is not None and wd is not None and md+MAP_MARGIN<wd:cls='map'
    elif pd is not None and pd<STATIC_MARGIN:cls='static-nonworld'
    else:cls='ambiguous'
    return dict(cls=cls,mapdiff=md,worlddiff=wd,dark=round(dark,3),prev_diff=pd)


def stats(ts):
    """Present intervals from a device-monotonic nanosecond list."""
    if len(ts)<2:return dict(available=False,frames=len(ts))
    intervals=[(b-a)/1e6 for a,b in zip(ts,ts[1:])]
    span=(ts[-1]-ts[0])/1e9
    if span<=0:return dict(available=False,frames=len(ts))
    return dict(available=True,frames=len(ts),seconds=span,presents_per_s=(len(ts)-1)/span,
                p50_ms=percentile(intervals,.5),p95_ms=percentile(intervals,.95),
                p99_ms=percentile(intervals,.99),max_ms=max(intervals),
                over_1000ms=sum(1 for x in intervals if x>1000))


def pooled(windows):
    """Pooled present rate across several frame-time lists."""
    usable=[ts for ts in windows if len(ts)>=2]
    if not usable:return dict(available=False,frames=sum(len(ts) for ts in windows))
    intervals=[(b-a)/1e6 for ts in usable for a,b in zip(ts,ts[1:])]
    span=sum(ts[-1]-ts[0] for ts in usable)/1e9
    return dict(available=True,frames=sum(len(ts) for ts in usable),seconds=span,
                presents_per_s=sum(len(ts)-1 for ts in usable)/span,
                p50_ms=percentile(intervals,.5),p95_ms=percentile(intervals,.95),
                p99_ms=percentile(intervals,.99),max_ms=max(intervals),
                over_1000ms=sum(1 for x in intervals if x>1000))


def delta(on,off):
    if not on.get('available') or not off.get('available'):return None
    return dict(presents_per_s=on['presents_per_s']-off['presents_per_s'],
                p95_ms=on['p95_ms']-off['p95_ms'])


def load_frames(path):
    with gzip.open(path,'rt',errors='replace') as f:
        return [(int(a),int(b)) for a,b in re.findall(r'MOMO_FRAME frame=(\d+) ns=(\d+)',f.read())]


def input_receipts(root):
    receipts={}
    for path in sorted(root.glob('*-input.json')):
        receipts[path.name[:-len('-input.json')]]=json.loads(path.read_text())
    return receipts


def trial(root):
    receipt=json.loads((root/'receipt.json').read_text())
    env=json.loads((root/'effective-env.json').read_text())
    frames=load_frames(root/'runtime.log.gz')
    stages=receipt['stages']
    end=max([t for _,t in frames]+[s['t_ns'] for s in stages])
    windows={}
    for i,s in enumerate(stages):
        lo=s['t_ns'];hi=stages[i+1]['t_ns'] if i+1<len(stages) else end
        windows[s['name']]=(lo,hi,float(s.get('watchdog_budget_s') or 0))
    phase_frames={name:[t for _,t in frames if lo<=t<hi] for name,(lo,hi,_) in windows.items()}
    receipts=input_receipts(root)
    walk_names=[s['name'] for s in stages if s['name'].startswith('walk-')]
    actions=[];hold_all=[];prev_capture=None
    for name in walk_names:
        capture=root/(name+'.png')
        info:dict=classify_shot(capture,root/'map.png',root/'world.png',prev_capture)
        r=receipts.get(name) or {}
        hold=[t for _,t in frames if r.get('sent_end_ns') and
              r['sent_end_ns']<=t<r['sent_end_ns']+r['hold_ms']*1_000_000]
        hold_all.append(hold)
        info.update(name=name,hold=stats(hold),hold_t=hold,hold_ms=r.get('hold_ms'))
        actions.append(info)
        if capture.exists():prev_capture=capture
    clean=[a['hold_t'] for a in actions if a['cls']=='world']
    capture_windows=[[t for _,t in frames if r['capture_begin_ns']<=t<r['capture_end_ns']]
                     for r in receipts.values() if r.get('capture_begin_ns') and r.get('capture_end_ns')]
    ledger=[json.loads(line) for line in (root/'ledger.jsonl').read_text().splitlines()
            if '"t_begin_ns"' in line]
    def med(rows,getter):
        values=[v for v in (getter(r) for r in rows) if isinstance(v,(int,float))]
        return statistics.median(values) if values else None
    memory={}
    for name in windows:
        rows=[r for r in ledger if r.get('phase')==name]
        if not rows:continue
        item=dict(samples=len(rows),
            pss_kib=med(rows,lambda r:r['rollup'].get('Pss')),
            swap_pss_kib=med(rows,lambda r:r['rollup'].get('SwapPss')),
            mem_available_kib_min=min((r['meminfo'].get('MemAvailable',0) for r in rows),default=None),
            mali_commit_bytes=med(rows,lambda r:r['mali'].get('commit_bytes')))
        if len(rows)>1:
            item['majflt_delta']=rows[-1]['process'].get('majflt',0)-rows[0]['process'].get('majflt',0)
            item['pswpin_delta']=rows[-1]['vmstat'].get('pswpin',0)-rows[0]['vmstat'].get('pswpin',0)
            item['pswpout_delta']=rows[-1]['vmstat'].get('pswpout',0)-rows[0]['vmstat'].get('pswpout',0)
        memory[name]=item
    def stalls_in(lo,hi,tag,label,threshold_ms=1000):
        found=[]
        ts=[t for _,t in frames if lo<=t<hi]
        for a,b in zip(ts,ts[1:]):
            if (b-a)/1e6>threshold_ms:
                entry=dict(trial=label,where=tag,at_s=round((a-lo)/1e9,2),gap_s=round((b-a)/1e9,2))
                near=[r for r in ledger if abs(r['t_begin_ns']-a)<8e9]
                if len(near)>1:
                    entry['majflt_near']=near[-1]['process'].get('majflt',0)-near[0]['process'].get('majflt',0)
                    entry['mem_available_min_kib']=min(r['meminfo'].get('MemAvailable',0) for r in near)
                found.append(entry)
        return found
    label=receipt['label']
    stalls=[]
    for name,(lo,hi,_) in windows.items():
        if name=='game-idle' or name.startswith('walk-'):
            stalls+=stalls_in(lo,hi,'phase:'+name,label)
    for name,r in receipts.items():
        if name.startswith('walk-') and r.get('sent_end_ns') and r.get('hold_ms'):
            stalls+=stalls_in(r['sent_end_ns'],r['sent_end_ns']+r['hold_ms']*1_000_000,'hold:'+name,label,500)
    ids=[i for i,_ in frames]
    classes={}
    for a in actions:classes[a['cls']]=classes.get(a['cls'],0)+1
    return dict(label=label,variant='720' if env.get('WOL_UPRENDER_720')=='1' else '1080',
                failure=receipt.get('failure'),cleanup_verified=receipt.get('cleanup_verified'),
                cleanup_warnings=receipt.get('cleanup_warnings'),runtime_sha256=receipt['runtime_sha256'],
                section_sha256=receipt['section_sha256'],control_save_hashes=receipt['control_save_hashes'],
                progress_checks=receipt.get('progress_checks'),present_watchdog_s=receipt.get('present_watchdog_s'),
                settled_watchdog_s=receipt.get('settled_watchdog_s'),
                frames_total=len(frames),frame_id_gaps=sum(1 for a,b in zip(ids,ids[1:]) if b!=a+1),
                phases={name:dict(window_s=(hi-lo)/1e9,settled=(name=='game-idle' or name.startswith('walk-')),
                                  watchdog_budget_s=budget,**stats(phase_frames[name]))
                        for name,(lo,hi,budget) in windows.items()},
                actions=actions,walk_classes=classes,
                moving=pooled([phase_frames[n] for n in phase_frames if n.startswith('walk-')]),
                moving_hold=pooled(clean),moving_hold_all=pooled(hold_all),capture=pooled(capture_windows),
                idle=stats(phase_frames.get('game-idle',[])),
                map=stats(phase_frames.get('map',[])),pause=stats(phase_frames.get('pause',[])),
                stalls=stalls,memory=memory,screenshots=sorted(p.name for p in root.glob('*.png')))


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--dir',type=Path,default=Path('evidence/accept-720'))
    ap.add_argument('--out',type=Path)
    a=ap.parse_args();root=Path(__file__).resolve().parent.parent/a.dir
    batch=json.loads((root/'batch.json').read_text())
    runs={}
    for label in batch['order']:
        trial_dir=root/label
        if not (trial_dir/'receipt.json').exists():continue
        runs[label]=trial(trial_dir)
    if len(runs)!=len(batch['order']):raise SystemExit('incomplete trials: %s'%sorted(set(batch['order'])-set(runs)))
    identity=dict(runtime_sha256=sorted({t['runtime_sha256'] for t in runs.values()}),
                  section_sha256=sorted({t['section_sha256'] for t in runs.values()}),
                  saves_equal=len({json.dumps(t['control_save_hashes'],sort_keys=True) for t in runs.values()})==1,
                  all_clean=all(t['cleanup_verified'] and not t['failure'] and not t['cleanup_warnings']
                                for t in runs.values()))
    pairs=[]
    for l1,l2 in PAIRS:
        t1,t2=runs[l1],runs[l2]
        off,on=(t1,t2) if t1['variant']=='1080' else (t2,t1)
        pairs.append(dict(pair=l1+'/'+l2,order=t1['variant']+'->'+t2['variant'],
            valid=t1['variant']!=t2['variant'] and identity['all_clean'],
            hold=delta(on['moving_hold'],off['moving_hold']),
            hold_all=delta(on['moving_hold_all'],off['moving_hold_all']),
            stage=delta(on['moving'],off['moving']),idle=delta(on['idle'],off['idle']),
            swap_pss_idle=((on['memory'].get('game-idle') or {}).get('swap_pss_kib') or 0)-
                          ((off['memory'].get('game-idle') or {}).get('swap_pss_kib') or 0),
            pss_idle=((on['memory'].get('game-idle') or {}).get('pss_kib') or 0)-
                     ((off['memory'].get('game-idle') or {}).get('pss_kib') or 0)))
    signs=[p['hold']['presents_per_s'] for p in pairs if p['valid'] and p['hold']]
    on_hold=[t['moving_hold'] for t in runs.values() if t['variant']=='720' and t['moving_hold'].get('available')]
    checks=dict(all_trials_clean=identity['all_clean'],
                hold_gain_moving=[round(x,2) for x in signs],
                hold_gain_consistent=bool(signs) and all(x>0 for x in signs),
                moving_720_fps=[round(s['presents_per_s'],2) for s in on_hold],
                moving_720_p95_ms=[round(s['p95_ms'],1) for s in on_hold],
                walk_classes={k:v['walk_classes'] for k,v in runs.items()},
                stalls=sum(len(t['stalls']) for t in runs.values()))
    summary=dict(schema=3,order=batch['order'],identity=identity,checks=checks,pairs=pairs,trials=runs,
                 caveats=['Runtime presents are not independent panel FPS.',
                          'Walk captures are classified against the trial\u2019s own map/world references; '
                          'non-world windows are excluded from moving_hold (moving_hold_all keeps the raw pool).',
                          'This is one save/scene family; interior, combat, dialogue, save/load and endurance are not covered.'])
    out=a.out or (root/'summary.json')
    out.write_text(json.dumps(summary,indent=2)+'\n')
    for label,t in runs.items():
        h=t['moving_hold'];ha=t['moving_hold_all']
        print('%-10s %s idle %6.2f/%5.1f | hold %6.2f/%5.1f (all %6.2f) | classes %s | swapPSS %6.1f | stalls %d'%(
            label,t['variant'],t['idle'].get('presents_per_s',0),t['idle'].get('p95_ms',0),
            h.get('presents_per_s',0),h.get('p95_ms',0),ha.get('presents_per_s',0),
            json.dumps(t['walk_classes']),(t['memory'].get('game-idle') or {}).get('swap_pss_kib',0)/1024,
            len(t['stalls'])))
    for p in pairs:
        d=p['hold'] or {}
        print('PAIR %s (%s) %s dHoldFPS %+6.2f (p95 %+6.1f) dHoldAll %+6.2f dIdle %+6.2f swapPSS d%+6.1f MiB'%(
            p['pair'],p['order'],'VALID' if p['valid'] else 'INVALID',d.get('presents_per_s',0),d.get('p95_ms',0),
            (p['hold_all'] or {}).get('presents_per_s',0),(p['idle'] or {}).get('presents_per_s',0),
            p['swap_pss_idle']/1024))
    for t in runs.values():
        for s in t['stalls']:
            print('STALL',json.dumps(s))
        for a_ in t['actions']:
            if a_['cls']!='world':
                print('NONWORLD',t['label'],a_['name'],a_['cls'],'mapdiff',a_['mapdiff'],'worlddiff',a_['worlddiff'],
                      'dark',a_['dark'],'prev',a_['prev_diff'])
    print('CHECKS',json.dumps({k:v for k,v in checks.items() if k!='walk_classes'}))


if __name__=='__main__':main()

#!/usr/bin/env python3
"""Summarize the sparse TransferMemory paired repeat (roadmap §16.5).

Variant = T2_TRANSFER_SPARSE_COPY with the accepted 720 trace-off profile otherwise fixed.
Moving stats use the 2 s input-hold windows. Per-VMA sums come from receipt `vma_samples`
(top_by_swap, anon 60..90 MiB = the cold transfer backing plus merged neighbor). All values
are page-accounting observations, never a summed physical total.
"""
from pathlib import Path
import argparse
import json
import statistics

from wol_accept_720_report import input_receipts, load_frames, pooled, stats

PAIRS=(('sparse-a1','sparse-b1'),('sparse-b2','sparse-a2'),('sparse-a3','sparse-b3'))
PHASES=('startup','menu','game-idle','precleanup')


def sparse_vma(rows):
    """The cold TransferMemory backing VMA: anon, 60..90 MiB, most swapped."""
    candidates=[r for r in rows if str(r.get('path','')).startswith('[anon') and
                60<=r.get('size_mib',0)<=90 and r.get('swap_mib',0)>0]
    return max(candidates,key=lambda r:r['swap_mib'],default=None)


def trial(root):
    receipt=json.loads((root/'receipt.json').read_text())
    env=json.loads((root/'effective-env.json').read_text())
    frames=load_frames(root/'runtime.log.gz')
    stages=receipt['stages']
    end=max([t for _,t in frames]+[s['t_ns'] for s in stages])
    windows={}
    for i,s in enumerate(stages):
        lo=s['t_ns'];hi=stages[i+1]['t_ns'] if i+1<len(stages) else end
        windows[s['name']]=(lo,hi)
    phase_frames={name:[t for _,t in frames if lo<=t<hi] for name,(lo,hi) in windows.items()}
    receipts=input_receipts(root)
    hold_windows=[]
    for name,r in receipts.items():
        if name.startswith('walk-') and r.get('sent_end_ns') and r.get('hold_ms'):
            hold_windows.append([t for _,t in frames if r['sent_end_ns']<=t<r['sent_end_ns']+r['hold_ms']*1_000_000])
    ledger=[json.loads(line) for line in (root/'ledger.jsonl').read_text().splitlines()
            if '"t_begin_ns"' in line]
    def med(rows,getter):
        values=[v for v in (getter(r) for r in rows) if isinstance(v,(int,float))]
        return statistics.median(values) if values else None
    memory={}
    for name in PHASES:
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
    vma={}
    for tag,doc in (receipt.get('vma_samples') or {}).items():
        if 'totals' not in doc:continue
        entry=dict(totals=doc['totals'])
        picked=sparse_vma(doc.get('top_by_swap',[]))
        if picked:
            entry['transfer_vma']=dict(size_mib=picked['size_mib'],swap_mib=picked['swap_mib'],
                                       rss_mib=picked['rss_mib'],pss_mib=picked['pss_mib'])
        vma[tag]=entry
    stalls=0
    for name,(lo,hi) in windows.items():
        if name=='game-idle' or name.startswith('walk-'):
            ts=[t for _,t in frames if lo<=t<hi]
            stalls+=sum(1 for a,b in zip(ts,ts[1:]) if (b-a)/1e6>1000)
    ids=[i for i,_ in frames]
    return dict(label=receipt['label'],variant='ON' if env.get('T2_TRANSFER_SPARSE_COPY')=='1' else 'OFF',
                failure=receipt.get('failure'),cleanup_verified=receipt.get('cleanup_verified'),
                cleanup_warnings=receipt.get('cleanup_warnings'),runtime_sha256=receipt['runtime_sha256'],
                section_sha256=receipt['section_sha256'],control_save_hashes=receipt['control_save_hashes'],
                progress_checks=receipt.get('progress_checks'),
                frames_total=len(frames),frame_id_gaps=sum(1 for a,b in zip(ids,ids[1:]) if b!=a+1),
                moving_hold=pooled(hold_windows),idle=stats(phase_frames.get('game-idle',[])),
                stalls=stalls,memory=memory,vma=vma,
                sparse_printf=[line for line in __import__('gzip').open(root/'runtime.log.gz','rt',errors='replace')
                               if line.startswith('T2_TRANSFER_SPARSE_COPY ')],
                screenshots=sorted(p.name for p in root.glob('*.png')))


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--dir',type=Path,default=Path('evidence/transfer-sparse-repeat'))
    a=ap.parse_args();root=Path(__file__).resolve().parent.parent/a.dir
    batch=json.loads((root/'batch.json').read_text())
    runs={}
    for label in batch['order']:
        d=root/label
        if (d/'receipt.json').exists():runs[label]=trial(d)
    if len(runs)!=len(batch['order']):raise SystemExit('incomplete trials: %s'%sorted(set(batch['order'])-set(runs)))
    identity=dict(runtime_sha256=sorted({t['runtime_sha256'] for t in runs.values()}),
                  section_sha256=sorted({t['section_sha256'] for t in runs.values()}),
                  saves_equal=len({json.dumps(t['control_save_hashes'],sort_keys=True) for t in runs.values()})==1,
                  all_clean=all(t['cleanup_verified'] and not t['failure'] and not t['cleanup_warnings']
                                for t in runs.values()))
    pairs=[]
    for l1,l2 in PAIRS:
        t1,t2=runs[l1],runs[l2]
        off,on=(t1,t2) if t1['variant']=='OFF' else (t2,t1)
        item=dict(pair=l1+'/'+l2,order=t1['variant']+'->'+t2['variant'],
                  valid=t1['variant']!=t2['variant'] and identity['all_clean'])
        for phase in PHASES:
            a_=off['memory'].get(phase) or {};b_=on['memory'].get(phase) or {}
            item['swap_pss_delta_%s'%phase]=(b_.get('swap_pss_kib') or 0)-(a_.get('swap_pss_kib') or 0)
            item['pss_delta_%s'%phase]=(b_.get('pss_kib') or 0)-(a_.get('pss_kib') or 0)
        for tag in ('startup','game-idle','precleanup'):
            ov=(off['vma'].get(tag) or {}).get('transfer_vma');nv=(on['vma'].get(tag) or {}).get('transfer_vma')
            if ov and nv:
                item['transfer_vma_swap_delta_mib_%s'%tag]=nv['swap_mib']-ov['swap_mib']
        h_off,h_on=off['moving_hold'],on['moving_hold']
        item['moving_hold_parity_fps']=(h_on.get('presents_per_s',0)-h_off.get('presents_per_s',0)
                                        if h_off.get('available') and h_on.get('available') else None)
        item['stalls_off']=off['stalls'];item['stalls_on']=on['stalls']
        pairs.append(item)
    swap_signs=[p.get('swap_pss_delta_game-idle') for p in pairs if p['valid']]
    summary=dict(schema=1,protocol=batch.get('protocol'),order=batch['order'],identity=identity,pairs=pairs,trials=runs,
                 checks=dict(all_trials_clean=identity['all_clean'],
                             swap_pss_delta_game_idle=[round(x/1024,1) for x in swap_signs if x is not None],
                             swap_reduction_consistent=bool(swap_signs) and all(x<0 for x in swap_signs),
                             moving_parity_fps=[round(p['moving_hold_parity_fps'],2) for p in pairs
                                                if p['moving_hold_parity_fps'] is not None],
                             stalls=[p['stalls_off']+p['stalls_on'] for p in pairs]),
                 caveats=['Page accounting only; no summed physical total; sequential snapshots.',
                          'Runtime presents are not independent panel FPS.',
                          'This is one save/scene family; promotion requires the full §16.5 sequence.'])
    out=root/'summary.json'
    out.write_text(json.dumps(summary,indent=2)+'\n')
    for label,t in runs.items():
        h=t['moving_hold'];gi=t['memory'].get('game-idle') or {}
        print('%-9s %s | moving %6.2f | swapPSS idle %6.1f precleanup %6.1f startup %6.1f | exits %d'%(
            label,t['variant'],h.get('presents_per_s',0),
            (gi.get('swap_pss_kib') or 0)/1024,
            ((t['memory'].get('precleanup') or {}).get('swap_pss_kib') or 0)/1024,
            ((t['memory'].get('startup') or {}).get('swap_pss_kib') or 0)/1024,len(t['sparse_printf'])))
    for p in pairs:
        print('PAIR %s (%s) %s dSwapPSS idle %+.1f pre %+.1f startup %+.1f MiB | xferVMA dSwap %s | moving parity %+.2f fps | stalls %d+%d'%(
            p['pair'],p['order'],'VALID' if p['valid'] else 'INVALID',
            p.get('swap_pss_delta_game-idle',0)/1024,p.get('swap_pss_delta_precleanup',0)/1024,
            p.get('swap_pss_delta_startup',0)/1024,
            json.dumps({k:v for k,v in p.items() if k.startswith('transfer_vma_swap_delta')}),
            p['moving_hold_parity_fps'] or 0,p['stalls_off'],p['stalls_on']))
    print('CHECKS',json.dumps(summary['checks']))


if __name__=='__main__':main()

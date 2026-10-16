#!/usr/bin/env python3
"""Compare two m1m5 benchmark runs (phase JSONs + runtime logs) for the VBO A/B."""
import json, lzma, re, sys
from pathlib import Path

def load(p):
    return json.loads(p.read_text())

def presents(phase):
    return phase['summary'].get('presents_per_s')

def log_stats(text):
    out={}
    periods=[];replays=[];finishes=[]
    for m in re.finditer(r'T2P_SLOW_FRAME frame=(\d+) period-ms=([\d.]+) replay-ms=([\d.]+) finish-ms=([\d.]+) present-ms=([\d.]+) swap-ms=([\d.]+) readback-ms=([\d.]+)', text):
        periods.append(float(m.group(2)));replays.append(float(m.group(3)));finishes.append(float(m.group(4)))
    def mean(x): return round(sum(x)/len(x),2) if x else None
    out['slow_frames']=len(periods)
    out['slow_period_mean_ms']=mean(periods)
    out['slow_replay_mean_ms']=mean(replays)
    out['slow_finish_mean_ms']=mean(finishes)
    up=[];by=[];hits=[]
    for m in re.finditer(r'NVN_STREAM_VBO_PROFILE after-frame=\d+ frames=(\d+) submits=(\d+) uploads=(\d+) bytes=(\d+) hits=(\d+) overflows=(\d+)', text):
        up.append(int(m.group(3)));by.append(int(m.group(4)));hits.append(int(m.group(5)))
    if up:
        out['stream_vbo_profiles']=len(up)
        out['stream_vbo_uploads_mean']=round(sum(up)/len(up),1)
        out['stream_vbo_bytes_mean']=round(sum(by)/len(by))
        out['stream_vbo_hits_mean']=round(sum(hits)/len(hits),1)
    out['stream_vbo_active']='NVN_STREAM_VBO_EXPERIMENT enabled=1' in text
    ring='WOL_PAIR_RING mode=reuse' in text
    if ring: out['pair_ring']='reuse'
    elif 'WOL_PAIR_RING mode=per-draw-gen-delete' in text: out['pair_ring']='per-draw-gen-delete'
    else: out['pair_ring']='not-logged'
    return out

def summarize(label_dir, log_path):
    print('===',label_dir)
    r=load(Path(label_dir)/'receipt.json')
    print('runtime_sha256',r.get('runtime_sha256','?')[:16],'cleanup_verified',r.get('cleanup_verified'))
    for phase in ('menu','game'):
        f=Path(label_dir)/(phase+'.json')
        if f.exists():
            d=load(f)
            print(f'  {phase:5s} presents/s={presents(d)}  PSS+SwapPSS_KiB={d["summary"].get("end_PSS_plus_SwapPSS_KiB")}')
    if log_path and Path(log_path).exists():
        text=Path(log_path).read_text(errors='replace')
        print('  log:',json.dumps(log_stats(text)))

if __name__=='__main__':
    summarize(sys.argv[1], sys.argv[2] if len(sys.argv)>2 else None)

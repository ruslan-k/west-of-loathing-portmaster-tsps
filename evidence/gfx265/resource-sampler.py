#!/usr/bin/env python3
"""Read-only bounded WoL /proc profile; no clock, VM, affinity or runtime changes."""
from pathlib import Path
import collections, datetime, json, os, re, sys, time

pid=int(sys.argv[1]); seconds=int(sys.argv[2]); output=Path(sys.argv[3])
assert 1<=seconds<=120
proc=Path('/proc')/str(pid)
log=Path('/mnt/SDCARD/Roms/PORTS/wol-switch/logs/latest.log')
hz=os.sysconf('SC_CLK_TCK'); page=os.sysconf('SC_PAGE_SIZE')
def text(p):
    try:return Path(p).read_text()
    except OSError:return ''
def kv(s):
    out={}
    for line in s.splitlines():
        a=line.replace(':',' ').split()
        if len(a)>1 and a[1].isdigit():out[a[0]]=int(a[1])
    return out

def stat(p):
    s=(p/'stat').read_text();a=s[s.rindex(')')+2:].split()
    return dict(start=int(a[19]),cpu_ticks=int(a[11])+int(a[12]),majflt=int(a[9]),minflt=int(a[7]))

identity=stat(proc)['start']
def threads():
    out={}
    for p in (proc/'task').iterdir():
        try:
            st=stat(p); status=text(p/'status')
            st.update(name=text(p/'comm').strip(),affinity=next((l.split(':',1)[1].strip() for l in status.splitlines() if l.startswith('Cpus_allowed_list:')),None))
            out[p.name]=st
        except OSError:pass
    return out

def mappings():
    out=[];r=None
    for l in text(proc/'smaps').splitlines():
        if re.match(r'^[0-9a-f]+-[0-9a-f]+ ',l):
            if r:out.append(r)
            parts=l.split(None,5);r={'mapping':parts[0],'perms':parts[1],'path':parts[5] if len(parts)>5 else '[anonymous]'}
        elif r:
            a=l.replace(':',' ').split()
            if len(a)>1 and a[1].isdigit():r[a[0]]=int(a[1])
    if r:out.append(r)
    return sorted(out,key=lambda r:r.get('Pss',0)+r.get('SwapPss',r.get('Swap',0)),reverse=True)

def sample():
    st=stat(proc);assert st['start']==identity,'PID reused'
    return dict(t=time.monotonic(),process=st,status=kv(text(proc/'status')),meminfo=kv(text('/proc/meminfo')),vmstat=kv(text('/proc/vmstat')),cpu_stat=text('/proc/stat'),pressure={k:text('/proc/pressure/'+k) for k in ('cpu','io','memory')},log_bytes=log.stat().st_size,io=kv(text(proc/'io')))

start_threads=threads();rollup_start=kv(text(proc/'smaps_rollup'));maps_start=mappings()
samples=[sample()]
for i in range(seconds//2):
    time.sleep(2);samples.append(sample())
end_threads=threads();rollup_end=kv(text(proc/'smaps_rollup'));maps_end=mappings()
a,b=samples[0],samples[-1];dt=b['t']-a['t']
clock_paths=list(Path('/sys/devices/system/cpu/cpufreq').glob('policy*/*freq'))+list(Path('/sys/class/devfreq').glob('*/*freq'))+list(Path('/sys/class/power_supply').glob('*/capacity'))
clocks={str(p):text(p).strip() for p in clock_paths if p.name in ('scaling_cur_freq','cpuinfo_cur_freq','scaling_min_freq','scaling_max_freq','cur_freq','min_freq','max_freq','capacity')}
top=[]
for tid,r in end_threads.items():
    if tid not in start_threads:continue
    delta=r['cpu_ticks']-start_threads[tid]['cpu_ticks']
    top.append(dict(tid=tid,name=r['name'],affinity=r['affinity'],cpu_percent=delta/hz/dt*100))
summary=dict(seconds=dt,cpu_percent=(b['process']['cpu_ticks']-a['process']['cpu_ticks'])/hz/dt*100,major_faults_per_s=(b['process']['majflt']-a['process']['majflt'])/dt,log_bytes_per_s=(b['log_bytes']-a['log_bytes'])/dt,system_swapin_KiB_per_s=(b['vmstat'].get('pswpin',0)-a['vmstat'].get('pswpin',0))*page/1024/dt,system_swapout_KiB_per_s=(b['vmstat'].get('pswpout',0)-a['vmstat'].get('pswpout',0))*page/1024/dt,top_threads=sorted(top,key=lambda r:r['cpu_percent'],reverse=True)[:12])
result=dict(schema=1,recorded_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),pid=pid,start_ticks=identity,hz=hz,page_bytes=page,summary=summary,samples=samples,rollup_start=rollup_start,rollup_end=rollup_end,maps_start=maps_start,maps_end=maps_end,clocks=clocks,online_cpus=text('/sys/devices/system/cpu/online').strip(),env={k:v for k,v in (e.split('=',1) for e in (proc/'environ').read_bytes().decode().strip('\0').split('\0') if '=' in e) if k.startswith(('WOL_','COTM_','T2_'))})
output.write_text(json.dumps(result,indent=2))
with log.open('rb') as f:
    f.seek(a['log_bytes']);chunk=f.read(b['log_bytes']-a['log_bytes'])
(output.parent/(output.stem+'.runtime-interval.log')).write_bytes(chunk)
print(json.dumps(dict(summary=summary,rollup_end=rollup_end,clocks=clocks,top_mappings=maps_end[:5]),indent=2))

#!/usr/bin/env python3
"""Bounded read-only exact-ELF resource/counter sampler, no graphics calls."""
from pathlib import Path
import argparse, hashlib, json, os, struct, time
from wol_memory_ledger import sample
from wol_memory_profile import Observer, stat_identity

def optional_text(path):
 try:return path.read_text()
 except OSError:return None

p=argparse.ArgumentParser()
p.add_argument('--label',required=True)
p.add_argument('--layout',type=Path,required=True)
p.add_argument('--out',type=Path,required=True)
p.add_argument('--phase-file',type=Path,required=True)
p.add_argument('--seconds',type=int,default=320)
a=p.parse_args()
assert 1<=a.seconds<=360 and all(c.isalnum() or c in '-_' for c in a.label)
l=json.loads(a.layout.read_text());assert l['member_bytes']==4 and l['member_offset']+4<=l['symbol_bytes']
end=time.monotonic()+a.seconds;ob=None
while time.monotonic()<end:
 found=[]
 for d in Path('/proc').iterdir():
  if not d.name.isdigit():continue
  try:
   if (d/'comm').read_text().strip()!='wol-horizon':continue
   env=dict(x.split('=',1) for x in (d/'environ').read_text().split('\0') if '=' in x)
   if env.get('WOL_RUN_LOG')==a.label:found.append((int(d.name),env))
  except OSError:pass
 if found:
  assert len(found)==1
  pid,env=found[0]
  for key in ('COTM_FRAMESKIP','AW_NO_PRESENT','MEGAMAN_LOGIC60_RENDER30'):assert env.get(key,'0')=='0',(key,env.get(key))
  ob=Observer(pid);assert ob.elf_sha256==l['elf_sha256'];break
 time.sleep(.5)
assert ob is not None,'owned runtime did not appear'
exe=os.readlink(ob.proc/'exe');maps=(ob.proc/'maps').read_text().splitlines()
base=next(int(parts[0].split('-')[0],16)-int(parts[2],16) for line in maps if len(parts:=line.split(None,5))==6 and parts[5]==exe and int(parts[2],16)==0)
address=base+l['symbol_offset']+l['member_offset'];fd=os.open(ob.proc/'mem',os.O_RDONLY)
try:
 with a.out.open('x') as out:
  out.write(json.dumps({'type':'header','pid':pid,'start_ticks':ob.identity,'elf_sha256':ob.elf_sha256,'counter_address':address,'layout':l,'effective_env':{k:v for k,v in env.items() if k.startswith(('WOL_','T2_','MOMO_','COTM_','AW_RELEASE'))},'clk_tck':os.sysconf('SC_CLK_TCK'),'method':'counter deltas across sampling endpoints; no per-frame latency or physical-refresh claim'})+'\n')
  while time.monotonic()<end:
   start=time.monotonic()
   try:
    ob.check();t0=time.monotonic_ns();raw=os.pread(fd,4,address)
    if len(raw)!=4:raise RuntimeError('owned runtime memory ended during final read')
    row=sample(ob,a.phase_file.read_text().strip() if a.phase_file.exists() else 'startup')
    row.update(frame_counter=struct.unpack('<I',raw)[0],counter_t_ns=t0,
     io=optional_text(ob.proc/'io'),gpu_util=optional_text(Path('/sys/kernel/debug/mali0/dvfs_utilization')),gpu_memory=optional_text(Path('/sys/kernel/debug/mali0/gpu_memory')))
    row['collector_end_ns']=time.monotonic_ns();ob.check()
   except (OSError,RuntimeError) as e:
    out.write(json.dumps({'type':'end','reason':str(e)})+'\n');out.flush();break
   out.write(json.dumps(row,separators=(',',':'))+'\n');out.flush()
   time.sleep(max(0,min(end-time.monotonic(),2-(time.monotonic()-start))))
finally:os.close(fd)
print('COLLECTOR_DONE',a.out,flush=True)

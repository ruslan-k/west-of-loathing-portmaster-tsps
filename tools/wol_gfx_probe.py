#!/usr/bin/env python3
"""Short principal-flow graphics test, literal env handoff and live KMS captures.
This is a device test, not a load-speed benchmark. It never changes sysctls.
"""
import argparse
import hashlib
import json
import lzma
from pathlib import Path
import shlex
import subprocess
import sys

REMOTE = r'''
import hashlib,json,os,pathlib,signal,subprocess,sys,time
port=pathlib.Path('/mnt/SDCARD/Roms/PORTS/wol-switch')
label=sys.argv[1]; seconds=int(sys.argv[2]); options=json.loads(sys.argv[3])
assert label.replace('-','').isalnum() and 20<=seconds<=900
logs=port/'logs'/label; logs.mkdir(exist_ok=False)
launch='/mnt/SDCARD/Roms/PORTS/West of Loathing Switch.sh'
standard='/mnt/SDCARD/Emu/PORTS/../../spruce/scripts/emu/standard_launch.sh'
cmd=pathlib.Path('/tmp/cmd_to_run.sh')
def pids(name):
 result=[]
 for p in pathlib.Path('/proc').iterdir():
  if not p.name.isdigit():continue
  try:
   if (p/'comm').read_text().strip()==name:result.append(int(p.name))
  except OSError:pass
 return result
def capture(name):
 for attempt in range(3):
  dst=logs/(name+'.png')
  r=subprocess.run(['/mnt/SDCARD/spruce/bin64/kmsgrab',str(dst)],capture_output=True,text=True,timeout=20)
  print('KMS',name,attempt,r.returncode,r.stdout.strip(),r.stderr.strip(),flush=True)
  if dst.exists() and dst.stat().st_size>100:return str(dst)
  time.sleep(.3)
 return None
def identity(pid):
 p=pathlib.Path('/proc')/str(pid)
 try:return ((p/'comm').read_text().strip(),str((p/'exe').resolve()),(p/'stat').read_text().rsplit(')',1)[1].split()[19])
 except OSError:return None
assert len(pids('MainUI'))==1 and not pids('wol-horizon'),'device is not idle'
assert not cmd.exists(),'existing handoff must not be overwritten'
capture('before-menu')
# Store values literally: neither SSH nor principal.sh inherit WOL_TEST_* from the host.
import shlex
line='env '+ ' '.join(shlex.quote(k+'='+v) for k,v in sorted(options.items()))+' '+shlex.quote(standard)+' '+shlex.quote(launch)+'\n'
cmd.write_text(line);cmd.chmod(0o755)
subprocess.run(['sh','-n',str(cmd)],check=True)
(logs/'handoff.sh').write_text(line)
marks=sorted(int(x) for x in options.get('WOL_CAPTURE_MARKS','15,45,90').split(','))
owned={}; seen=False; began=None; captures=set(); started=time.monotonic()
try:
 os.kill(pids('MainUI')[0],signal.SIGTERM)
 while time.monotonic()-started<seconds+45:
  live=pids('wol-horizon')
  if live:
   for pid in live:owned.setdefault(pid,identity(pid))
   if not seen:
    seen=True;began=time.monotonic();p=pathlib.Path('/proc')/str(live[0])
    actual=dict(x.split('=',1) for x in (p/'environ').read_bytes().decode().split(chr(0)) if '=' in x)
    selected={k:actual.get(k) for k in options}
    (logs/'effective-env.json').write_text(json.dumps(selected,indent=2))
    assert selected==options,('env mismatch',selected,options)
    print('RUNTIME',live,selected,flush=True)
   elapsed=time.monotonic()-began
   for mark in marks:
    if elapsed>=mark and mark not in captures:
     captures.add(mark);capture('during-'+str(mark))
     (logs/('status-'+str(mark)+'.txt')).write_text((pathlib.Path('/proc')/str(live[0])/'status').read_text())
   if elapsed>=seconds:break
  elif seen and pids('MainUI'):break
  time.sleep(.5)
finally:
 for pid,ident in owned.items():
  if ident and identity(pid)==ident:
   os.kill(pid,signal.SIGTERM)
 time.sleep(2)
 for pid,ident in owned.items():
  if ident and identity(pid)==ident:os.kill(pid,signal.SIGKILL)
 for _ in range(60):
  if pids('MainUI') and not pids('wol-horizon'):break
  time.sleep(.25)
 if cmd.exists() and cmd.read_text()==line and pids('MainUI'):cmd.unlink()
 time.sleep(1)
 capture('after-menu')
 print('FINAL_STATE',pids('MainUI'),pids('wol-horizon'),flush=True)
 assert pids('MainUI') and not pids('wol-horizon'),'cleanup incomplete'
print('RUNTIME_SEEN',seen,flush=True)
assert seen,'runtime was never observed'
'''

def main():
    p=argparse.ArgumentParser()
    p.add_argument('label');p.add_argument('--seconds',type=int,default=120)
    p.add_argument('--set',action='append',default=[])
    a=p.parse_args()
    assert a.label.replace('-','').isalnum()
    options={'WOL_PROBE_SECONDS':str(a.seconds),'WOL_MEMORY_FLOOR_MIB':'20',
             'WOL_QUIET':'1','WOL_PRESENT_TEST':'0','WOL_PAIR_TEST':'0',
             'WOL_FS_TESTTEX':'0','WOL_PAIR_MATH':'1','WOL_VS_TRIVIAL':'0',
             'WOL_COHERENCE':'0','WOL_DUMP':'0','WOL_F191_UV':'',
             'WOL_COMPOSITE_PROBE':'0','COTM_PRESENT_READBACK_60':'1',
             'COTM_READBACK_PERIOD':'600','COTM_CAPTURE_PERIOD':'600',
             'WOL_CAPTURE_MARKS':'15,45,90'}
    for item in a.set:
        k,v=item.split('=',1)
        assert k.startswith(('WOL_','COTM_')) and k.replace('_','').isalnum()
        options[k]=v
    repo=Path(__file__).resolve().parents[1]
    out=repo/'evidence'/a.label;out.mkdir(exist_ok=False)
    ssh=['ssh','-o','BatchMode=yes','-o','ConnectTimeout=10','root@192.168.50.135']
    command='python3 - '+shlex.join([a.label,str(a.seconds),json.dumps(options)])
    with (out/'harness.log').open('w') as f:
        r=subprocess.run(ssh+[command],input=REMOTE,text=True,stdout=f,stderr=subprocess.STDOUT,timeout=a.seconds+160)
    print('HARNESS_RC',r.returncode,flush=True)
    print((out/'harness.log').read_text(),flush=True)
    target='root@192.168.50.135:/mnt/SDCARD/Roms/PORTS/wol-switch/'
    subprocess.run(['scp','-O',target+'logs/'+a.label+'/*',str(out)],check=True)
    subprocess.run(['scp','-O',target+'logs/latest.log',str(out/'runtime.log')],check=True)
    raw=out/'runtime.log'
    digest=hashlib.sha256()
    with raw.open('rb') as f,lzma.open(str(raw)+'.xz','wb',preset=1) as z:
        for chunk in iter(lambda:f.read(1048576),b''):digest.update(chunk);z.write(chunk)
    (out/'runtime.sha256').write_text(digest.hexdigest()+'  runtime.log\n')
    print('EVIDENCE',out,'RAW_LOG_SHA256',digest.hexdigest(),flush=True)
    if r.returncode:raise SystemExit(r.returncode)

if __name__=='__main__':main()

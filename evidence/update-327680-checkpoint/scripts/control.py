#!/usr/bin/env python3
"""Exact-run, identity-bound diagnostic capture/input controller."""
from pathlib import Path
import argparse,hashlib,json,subprocess,time
W=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('label');p.add_argument('name');p.add_argument('--buttons',type=lambda s:int(s,0),default=0);p.add_argument('--ms',type=int,default=0);p.add_argument('--stick',default='0,0');p.add_argument('--delay',type=float,default=0);p.add_argument('--phase');a=p.parse_args()
assert all(c.isalnum() or c in '_-' for c in a.label+a.name)
assert 0<=a.ms<=1900 and 0<=a.delay<=15 and (a.buttons&0xc00)!=0xc00 and not a.buttons&~0xffff
x,y=map(int,a.stick.split(','));assert -32767<=x<=32767 and -32767<=y<=32767
expected_file=W/(a.label+'-control-identity.json');expected=json.loads(expected_file.read_text()) if expected_file.exists() else None
manifest=json.loads((W/'candidate/device-manifest.json').read_text());shot='/mnt/UDISK/wol-'+a.label+'-'+a.name+'.png'
values=dict(label=a.label,expected=expected,elf=manifest['runtime_sha256'],shot=shot,buttons=a.buttons,ms=a.ms,stick=(x&0xffff)|((y&0xffff)<<16),delay=a.delay,phase=a.phase)
body=r'''
from pathlib import Path
import os,json,hashlib,socket,struct,subprocess,time
found=[]
for p in Path('/proc').iterdir():
 if p.name.isdigit():
  try:
   c=(p/'comm').read_text().strip()
   if c=='MainUI':raise RuntimeError('MainUI active, refusing game action')
   if c=='wol-horizon':
    e=dict(x.split('=',1) for x in (p/'environ').read_text().split('\0') if '=' in x)
    found.append({'pid':int(p.name),'start':(p/'stat').read_text().rsplit(')',1)[1].split()[19],'label':e.get('WOL_RUN_LOG'),'elf':hashlib.sha256((p/'exe').read_bytes()).hexdigest(),'boot':Path('/proc/sys/kernel/random/boot_id').read_text().strip()})
  except OSError:pass
assert len(found)==1,found
s=found[0];assert s['label']==label and s['elf']==elf,s
if expected is not None:assert s==expected,(s,expected)
p=Path('/proc')/str(s['pid'])
def check():
 assert (p/'comm').read_text().strip()=='wol-horizon' and (p/'stat').read_text().rsplit(')',1)[1].split()[19]==s['start']
 assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==s['boot']
check()
if ms:
 inodes=set()
 for f in (p/'fd').iterdir():
  try:
   v=os.readlink(f)
   if v.startswith('socket:['):inodes.add(v[8:-1])
  except OSError:pass
 socks=[l.split()[-1] for l in Path('/proc/net/unix').read_text().splitlines()[1:] if len(l.split())>=8 and l.split()[6] in inodes and l.split()[-1].endswith('/buttons.sock')]
 assert len(socks)==1,socks
 check();sk=socket.socket(socket.AF_UNIX,socket.SOCK_DGRAM);sk.sendto(struct.pack('<QII',buttons,ms,stick),socks[0]);sk.close()
if phase:
 f=Path('/mnt/UDISK/wol-acceptance-327680')/(label+'.phase');f.write_text(phase);assert f.read_text()==phase
if delay:time.sleep(delay)
check();r=subprocess.run(['/mnt/SDCARD/spruce/bin64/kmsgrab',shot],capture_output=True,text=True,timeout=20);assert r.returncode==0,r.stdout+r.stderr
print(json.dumps({'identity':s,'capture':shot,'press':{'buttons':buttons,'ms':ms,'stick':stick},'phase':phase,'target_t_ns':time.monotonic_ns(),'kms':r.stdout+r.stderr}))
'''
code='\n'.join(k+'='+repr(v) for k,v in values.items())+'\n'+body;compile(code,'<owned-controller>','exec')
ssh=['ssh','-o','BatchMode=yes','-o','ControlMaster=no','-o','ControlPath=none','-o','ConnectTimeout=8','tsps'];r=subprocess.run(ssh+['python3','-'],input=code,text=True,capture_output=True,timeout=50)
if r.returncode:raise RuntimeError(r.returncode,r.stdout,r.stderr)
d=json.loads(r.stdout)
if expected is None:expected_file.write_text(json.dumps(d['identity'],indent=2)+'\n')
subprocess.run(['scp','-O','-q','-o','BatchMode=yes','-o','ControlMaster=no','-o','ControlPath=none','tsps:'+shot,str(W/Path(shot).name)],check=True,timeout=30)
(W/(a.label+'-'+a.name+'-receipt.json')).write_text(json.dumps(d,indent=2)+'\n');print(json.dumps(d,indent=2))

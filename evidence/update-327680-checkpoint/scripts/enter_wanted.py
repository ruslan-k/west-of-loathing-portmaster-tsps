#!/usr/bin/env python3
"""One diagnostic A only after a fresh KMS matches the verified update title."""
from pathlib import Path
import json,subprocess,sys,time,os,hashlib
sys.path.insert(0,'/mnt/external/Hermes/west-of-loathing-portmaster-tsps/tools')
from wol_screen_gate import read_rgb,fingerprint_match
W=Path(__file__).resolve().parent
SSH=['ssh','-o','BatchMode=yes','-o','ControlMaster=no','-o','ControlPath=none','-o','ConnectTimeout=8','tsps']
SCP=['scp','-O','-q','-o','BatchMode=yes','-o','ControlMaster=no','-o','ControlPath=none']
points=tuple((x,y) for y in range(267,324,5) for x in range(519,792,5))+tuple((x,y) for y in range(384,416,4) for x in range(562,733,5))
reference=Path(os.environ.get('WOL_TITLE_REFERENCE',str(W/'wol-r1-live.png')))
reference_sha=hashlib.sha256(reference.read_bytes()).hexdigest()
w,h,ref=read_rgb(reference)
assert (w,h)==(1280,720)
bits=''.join('1' if sum(ref[((y*w+x)*3):((y*w+x)*3+3)])<360 else '0' for x,y in points)
def observe(path):
 w,h,rgb=read_rgb(path)
 assert (w,h)==(1280,720)
 score,offset=fingerprint_match(w,rgb,points,bits,range(-12,13,2),range(-16,17,2))
 return {'title':score<=.14,'mismatch':score,'offset':offset,'samples':len(bits)}
if sys.argv[1:]==['--selftest']:
 assert observe(reference)['title']
 assert not observe(W/'wol-q1-after-a.png')['title']
 score,_=fingerprint_match(w,bytes([255])*len(ref),points,bits,[0],[0]);assert score>.14
 print('TITLE_GATE_SELFTEST_OK',observe(reference),score,reference_sha)
 raise SystemExit(0)
label=sys.argv[1];assert label and all(c.isalnum() or c in '-_' for c in label)
remote_body=r'''
from pathlib import Path
import os,json,socket,struct,subprocess,time
found=[]
for p in Path('/proc').iterdir():
 if p.name.isdigit():
  try:
   if (p/'comm').read_text().strip()=='wol-horizon':
    e=dict(x.split('=',1) for x in (p/'environ').read_text().split('\0') if '=' in x)
    found.append({'pid':int(p.name),'start':(p/'stat').read_text().rsplit(')',1)[1].split()[19],'label':e.get('WOL_RUN_LOG'),'elf':e.get('WOL_EXPECTED_ELF_SHA256')})
  except OSError:pass
assert len(found)<=1,found
if not found:print(json.dumps({'alive':False}))
else:
 s=found[0];assert s['label']==label,s
 if expected is not None:assert s==expected,(s,expected)
 if press:
  p=Path('/proc')/str(s['pid']);inodes=set()
  for fd in (p/'fd').iterdir():
   try:
    v=os.readlink(fd)
    if v.startswith('socket:['):inodes.add(v[8:-1])
   except OSError:pass
  socks=[l.split()[-1] for l in Path('/proc/net/unix').read_text().splitlines()[1:] if len(l.split())>=8 and l.split()[6] in inodes and l.split()[-1].endswith('/buttons.sock')]
  assert len(socks)==1,socks
  sock=socket.socket(socket.AF_UNIX,socket.SOCK_DGRAM);sock.sendto(struct.pack('<QII',1,80,0),socks[0]);sock.close()
 if shot:
  result=subprocess.run(['/mnt/SDCARD/spruce/bin64/kmsgrab',shot],capture_output=True,text=True,timeout=15)
  if result.returncode:raise RuntimeError(result.stdout+result.stderr)
 print(json.dumps({'alive':True,'identity':s,'capture':shot,'press':press}))
'''
def remote(shot=None,press=False,expected=None):
 vals={'label':label,'shot':shot,'press':press,'expected':expected}
 code='\n'.join(k+'='+repr(v) for k,v in vals.items())+'\n'+remote_body
 compile(code,'<input-gate>','exec')
 p=subprocess.run(SSH+['python3','-'],input=code,text=True,capture_output=True,timeout=30)
 if p.returncode:raise RuntimeError(p.returncode,p.stdout,p.stderr)
 return json.loads(p.stdout)
def capture(suffix,expected):
 path='/mnt/UDISK/wol-'+label+'-'+suffix+'.png';r=remote(path,expected=expected)
 if r['alive']:subprocess.run(SCP+['tsps:'+path,str(W/Path(path).name)],check=True,timeout=30)
 return r,W/Path(path).name
rows=[];identity=None;seen=False;stable=0;deadline=time.monotonic()+180
try:
 while time.monotonic()<deadline:
  state=remote(expected=identity)
  if not state['alive']:
   if seen:raise RuntimeError('owned runtime exited before verified title')
   time.sleep(2);continue
  seen=True;identity=state['identity']
  try:r,path=capture('before-a',identity)
  except RuntimeError as error:
   if 'No active framebuffers found on planes' not in str(error):raise
   rows.append({'title':False,'capture_error':'no active KMS framebuffer during startup'})
   time.sleep(2);continue
  if not r['alive']:raise RuntimeError('runtime exited at capture')
  observation=observe(path);rows.append(observation)
  print('READINESS',json.dumps(observation),flush=True)
  stable=stable+1 if observation['title'] else 0
  if stable>=2:
   remote(press=True,expected=identity);print('SENT_DIAGNOSTIC_A',json.dumps(identity),flush=True)
   for delay,suffix in [(1,'after-a1'),(3,'after-a4'),(4,'after-a8')]:
    time.sleep(delay);r,path=capture(suffix,identity);print('CAPTURE',json.dumps(r),flush=True)
    if not r['alive']:break
   break
  time.sleep(7)
 else:raise RuntimeError('no title readiness; input refused')
finally:
 (W/(label+'-input-readiness.json')).write_text(json.dumps({'identity':identity,'observations':rows,'title_reference_sha256':reference_sha,'physical_input_verified':False},indent=2)+'\n')

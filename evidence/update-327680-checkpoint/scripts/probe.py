#!/usr/bin/env python3
"""Local-only bounded v327680 experiment; never replace the playable port."""
from pathlib import Path
import hashlib
import json
import shlex
import subprocess
import sys
import time

W = Path(__file__).resolve().parent
D = '/mnt/SDCARD/Roms/PORTS/wol-update-probe-20261028'
STD = '/mnt/SDCARD/Emu/PORTS/../../spruce/scripts/emu/standard_launch.sh'
SSH = ['ssh', '-o', 'BatchMode=yes', '-o', 'ControlMaster=no', '-o', 'ControlPath=none', '-o', 'ConnectTimeout=8', 'tsps']
COMMON = r'''
from pathlib import Path
import os,json,hashlib,stat,subprocess,base64
D=Path(dpath)
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def procs():
 out=[]
 for p in Path('/proc').iterdir():
  if not p.name.isdigit():continue
  try:
   c=(p/'comm').read_text().strip();s=(p/'stat').read_text().rsplit(')',1)[1].split()
   if c in ('MainUI','wol-horizon','ua_host','principal.sh','runtime.sh'):
    out.append({'pid':int(p.name),'comm':c,'start':int(s[19]),'ppid':int(s[1]),'pgid':int(s[2]),'sid':int(s[3]),'exe':os.readlink(p/'exe')})
  except OSError:pass
 return out
'''

def source(body, values):
    code = '\n'.join(k + '=' + repr(v) for k, v in {'dpath': D, **values}.items()) + '\n' + COMMON + '\n' + body
    compile(code, '<remote>', 'exec')
    return code


def remote(body, **values):
    r = subprocess.run(SSH + ['python3', '-'], input=source(body, values), text=True, capture_output=True, timeout=110)
    if r.returncode:
        raise RuntimeError((r.returncode, r.stdout, r.stderr))
    return json.loads(r.stdout)


if sys.argv[1:] == ['--selftest']:
    value = "WOL_EXPECTED_ELF_SHA256='quoted value'\n"
    r = subprocess.run([sys.executable, '-c', source('print(json.dumps(command))', {'command': value})], capture_output=True, text=True, check=True)
    assert json.loads(r.stdout) == value
    print('REMOTE_LITERAL_ROUNDTRIP_OK')
    raise SystemExit(0)

label = sys.argv[1]
assert label and all(c.isalnum() or c in '_-' for c in label)
manifest = json.loads((W / 'candidate/device-manifest.json').read_text())
env = {'WOL_GAMEDIR': D, 'WOL_RUN_LOG': label, 'WOL_EXPECTED_ELF_SHA256': manifest['runtime_sha256'],
       'WOL_WATCHDOG_SECONDS': '300', 'WOL_PROBE_SECONDS': '260', 'WOL_CMA_MIN_KB': '65536',
       'WOL_MEMORY_FLOOR_MIB': '24', 'WOL_UPDATE_DRAFT': '1', 'WOL_PLACEHOLDER_DRAW': '0',
       'WOL_ROMFS_COW': '1', 'WOL_ROMFS_COW_POOL': '1', 'WOL_COMPOSITE_PROBE': '0', 'WOL_COMPOSE_TRACE': '1', 'WOL_PRESENT_TRACE': '0', 'WOL_TARGET_PROBE': '0', 'WOL_SHADER_DUMP': '1', 'WOL_NVN_TRACE': '1', 'WOL_UPDATE_CLIP_CONTROL': '1', 'COTM_INPUT_DIAGNOSTIC': '1', 'AW_RELEASE': '1'}
assert 0<int(env['WOL_PROBE_SECONDS'])<int(env['WOL_WATCHDOG_SECONDS'])<=300
if len(sys.argv)>2:
    assert sys.argv[2]=='fullkey', 'only the explicit fullkey control arm is supported'
    env['MOMO_NPAD_HANDHELD']='0'
command = 'export ' + ' '.join(k+'='+shlex.quote(v) for k,v in env.items()) + '; ' + shlex.quote(STD) + ' ' + shlex.quote(D+'/update-launcher.sh') + '\n'
subprocess.run(['sh', '-n'], input=command, text=True, check=True)
before = remote(r'''
q=Path('/tmp/cmd_to_run.sh');assert not q.exists() and not q.is_symlink()
ps=procs();assert len([p for p in ps if p['comm']=='MainUI'])==1 and not [p for p in ps if p['comm'] in ('wol-horizon','ua_host')],ps
main=next(p for p in ps if p['comm']=='MainUI');assert os.path.samefile('/mnt/SDCARD/spruce/flip/bin/MainUI','/proc/%d/exe'%main['pid'])
for x in expected['files']:
 p=D/x['path'];assert p.stat().st_size==x['bytes'] and sha(p)==x['sha256'],p
 with p.open('rb') as f:os.posix_fadvise(f.fileno(),0,0,os.POSIX_FADV_DONTNEED)
mem={l.split(':')[0]:int(l.split()[1]) for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith(('CmaFree:','MemAvailable:','SwapFree:'))}
# The per-run CMA gate runs in the launcher after MainUI releases its buffers.
assert mem['CmaFree']>=32768 and mem['MemAvailable']>=500000,mem
cpus={str(i):{'value':(Path('/sys/devices/system/cpu')/('cpu%d/online'%i)).read_text().strip(),'mode':stat.S_IMODE((Path('/sys/devices/system/cpu')/('cpu%d/online'%i)).stat().st_mode)} for i in range(8)}
prod=Path('/mnt/SDCARD/Roms/PORTS/westofloathing');production={str(p):sha(p) for p in (prod/'ua_host',Path('/mnt/SDCARD/Roms/PORTS/West of Loathing.sh'))}
for root in (prod/'home',prod/'data'):
 for p in root.rglob('*'):
  if p.is_file() and p.stat().st_size<1048576 and not any(x in p.parts for x in ('Managed','logs')):production[str(p)]=sha(p)
last=Path('/mnt/SDCARD/spruce/flags/lastgame.lock');assert not (D/'logs'/('diag-'+label+'.log')).exists()
print(json.dumps({'main':main,'procs':ps,'mem':mem,'cpus':cpus,'production':production,'lastgame':base64.b64encode(last.read_bytes()).decode() if last.exists() else None,'standard_sha256':sha(Path(standard)),'boot':Path('/proc/sys/kernel/random/boot_id').read_text().strip()}))
''', expected=manifest, label=label, standard=STD)
(W/(label+'-before.json')).write_text(json.dumps(before, indent=2))
print('PREFLIGHT', before['main'], before['mem'], flush=True)
hand = remote(r'''
q=Path('/tmp/cmd_to_run.sh');assert not q.exists() and not q.is_symlink()
assert procs()==before['procs'],procs()
assert sha(Path(standard))==before['standard_sha256']
for x in expected['files']:
 p=D/x['path'];assert sha(p)==x['sha256'],p
 with p.open('rb') as f:os.posix_fadvise(f.fileno(),0,0,os.POSIX_FADV_DONTNEED)
assert next(p for p in procs() if p['comm']=='MainUI')==before['main']
fd=os.open(q,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o700)
with os.fdopen(fd,'w') as f:f.write(command);f.flush();os.fsync(f.fileno())
assert q.read_text()==command
subprocess.run(['/bin/sh','-n',str(q)],check=True)
assert next(p for p in procs() if p['comm']=='MainUI')==before['main']
os.kill(before['main']['pid'],15)
print(json.dumps({'term_pid':before['main']['pid'],'start':before['main']['start'],'command_sha256':hashlib.sha256(command.encode()).hexdigest()}))
''', before=before, expected=manifest, command=command, standard=STD)
(W/(label+'-handoff.json')).write_text(json.dumps(hand, indent=2))
print('HANDOFF', hand, flush=True)
start=time.monotonic();seen=False;shots=[];samples=[];marks=iter([5,100,180,240]);mark=next(marks,None)
while time.monotonic()-start < 395:
    elapsed=time.monotonic()-start
    state=remote(r'''
L=D/'logs'/('diag-'+label+'.log')
mem={l.split(':')[0]:int(l.split()[1]) for l in Path('/proc/meminfo').read_text().splitlines() if l.startswith(('CmaFree:','MemAvailable:','SwapFree:'))}
print(json.dumps({'procs':procs(),'mem':mem,'tail':L.read_text(errors='replace')[-1600:] if L.exists() else '', 'log_bytes':L.stat().st_size if L.exists() else 0,'handoff':Path('/tmp/cmd_to_run.sh').exists()}))
''', label=label)
    samples.append({'elapsed':elapsed, **state})
    games=[p for p in state['procs'] if p['comm']=='wol-horizon'];uis=[p for p in state['procs'] if p['comm']=='MainUI']
    assert len(games)<=1 and not (games and uis),state
    seen=seen or bool(games)
    if games and mark is not None and elapsed>=mark:
        path='/mnt/UDISK/wol-'+label+'-'+str(mark)+'.png'
        shot=remote('r=subprocess.run(["/mnt/SDCARD/spruce/bin64/kmsgrab",path],capture_output=True,text=True,timeout=15)\nprint(json.dumps({"rc":r.returncode,"text":r.stdout+r.stderr}))', path=path)
        shots.append({'path':path,'elapsed':elapsed,**shot});mark=next(marks,None)
        print('CAPTURE', shots[-1], flush=True)
    if len(samples)%6==0:print('SAMPLE',round(elapsed,1),state['mem'],[(p['pid'],p['comm']) for p in state['procs']],state['tail'][-180:],flush=True)
    if not games and uis and not state['handoff'] and elapsed>10 and state['log_bytes']>0:break
    time.sleep(2)
(W/(label+'-observations.json')).write_text(json.dumps(samples,indent=2))
(W/(label+'-captures.json')).write_text(json.dumps(shots,indent=2))
assert not [p for p in state['procs'] if p['comm']=='wol-horizon'] and any(p['comm']=='MainUI' for p in state['procs']) and not state['handoff'],state
print('FINAL', seen, state, flush=True)
recovery='/mnt/UDISK/wol-'+label+'-recovered.png'
cleanup=remote(r'''
ps=procs();assert not [p for p in ps if p['comm'] in ('wol-horizon','ua_host')]
assert len([p for p in ps if p['comm']=='MainUI'])==1 and not Path('/tmp/cmd_to_run.sh').exists()
for name,expected_hash in before['production'].items():assert sha(Path(name))==expected_hash,name
cpus={str(i):{'value':(Path('/sys/devices/system/cpu')/('cpu%d/online'%i)).read_text().strip(),'mode':stat.S_IMODE((Path('/sys/devices/system/cpu')/('cpu%d/online'%i)).stat().st_mode)} for i in range(8)}
# standard_launch.sh restores read-only CPU modes after the port's own EXIT trap.
# Restore only our recorded permission drift, never online bits changed elsewhere.
assert Path('/proc/sys/kernel/random/boot_id').read_text().strip()==before['boot']
assert all(cpus[i]['value']==old['value'] for i,old in before['cpus'].items()),cpus
for i,old in before['cpus'].items():
 if cpus[i]['mode']!=old['mode']:os.chmod(Path('/sys/devices/system/cpu')/('cpu'+i)/'online',old['mode'])
cpus={str(i):{'value':(Path('/sys/devices/system/cpu')/('cpu%d/online'%i)).read_text().strip(),'mode':stat.S_IMODE((Path('/sys/devices/system/cpu')/('cpu%d/online'%i)).stat().st_mode)} for i in range(8)}
assert cpus==before['cpus'],cpus
import struct,time
with open('/dev/input/event4','wb',buffering=0) as f:
 for value in (-1,0):
  f.write(struct.pack('<qqHHi',0,0,3,16,value)+struct.pack('<qqHHi',0,0,0,0,0));time.sleep(.15)
time.sleep(1)
r=subprocess.run(['/mnt/SDCARD/spruce/bin64/kmsgrab',recovery],capture_output=True,text=True,timeout=20)
assert r.returncode==0,r.stdout+r.stderr
print(json.dumps({'procs':ps,'production_hashes_unchanged':len(before['production']),'cpu_restored':True,'kms':r.stdout+r.stderr}))
''', before=before, recovery=recovery)
(W/(label+'-cleanup.json')).write_text(json.dumps(cleanup,indent=2))
print('CLEANUP',cleanup,flush=True)
for path in [D+'/logs/diag-'+label+'.log',recovery]+[s['path'] for s in shots if s['rc']==0]:
    subprocess.run(['scp','-O','-q','-o','BatchMode=yes','-o','ControlMaster=no','-o','ControlPath=none','tsps:'+path,str(W/Path(path).name)],capture_output=True,text=True,check=True,timeout=90)
print('EVIDENCE',W)

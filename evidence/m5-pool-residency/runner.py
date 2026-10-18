from pathlib import Path
import subprocess,time,json,sys,shlex
repo=Path('/mnt/external/Hermes/west-of-loathing-portmaster-tsps')
ssh=['ssh','-o','ControlMaster=no','-o','ControlPath=none','-o','BatchMode=yes','-o','ConnectTimeout=15','tsps']
expected='273b4638cae6dd4d0cbe7d1b4a91eac9e3f68c6b758fb7ef2729a2c28e31af13'
def remote(s):return subprocess.run(ssh+[s],text=True,capture_output=True,check=True,timeout=45).stdout
for spec in sys.argv[1:]:
 label,flag=spec.split(':');assert flag in ('0','1') and label.replace('-','').isalnum()
 assert remote('sha256sum /mnt/SDCARD/Roms/PORTS/wol-switch/wol-horizon').split()[0]==expected
 args=['env','WOL_UPRENDER_TRACE=0','WOL_UPRENDER_720='+flag,'WOL_GUEST_RT720=0','WOL_RT_ORIGIN=0',
       'WOL_ROMFS_COW=0','WOL_UPLOAD_SKIP=0','WOL_UNIFORM_CACHE=0','WOL_COPY_EQUAL=0','WOL_ALLOC_TRACE=1',
       'WOL_COPY_AUDIT=0','WOL_GPU_TIMELINE=0','WOL_GPU_RESIDENCY=0',
       'python3','/mnt/UDISK/wol_roadmap_probe.py','--label',label,'--layout','/mnt/UDISK/wol-upscope2-layout.json',
       '--present-watchdog','20','--stall-gdb','--block-pages']
 remote('setsid nohup '+shlex.join(args)+' > /mnt/UDISK/'+label+'-run.log 2>&1 < /dev/null &')
 print('STARTED',label,flush=True);end=time.monotonic()+480
 while time.monotonic()<end:
  r=json.loads(remote('python3 -c '+shlex.quote('from pathlib import Path; p=Path("/mnt/UDISK/roadmap-v2-'+label+'/receipt.json"); print(p.read_text() if p.exists() else "{}")')))
  if r.get('cleanup_verified'):break
  if r.get('cleanup_warnings'):raise RuntimeError(r)
  time.sleep(8)
 else:raise RuntimeError(label+' incomplete; backup preserved')
 dest=repo/'evidence/m5-pool-residency'/label;dest.mkdir(parents=True,exist_ok=True)
 code='from pathlib import Path;import json;p=Path("/mnt/UDISK/roadmap-v2-'+label+'");print(json.dumps([str(x.relative_to(p)) for x in p.rglob("*") if x.is_file() and (x.name in ("receipt.json","effective-env.json","ledger.jsonl","runtime.log.gz","restored-menu.png") or "stall" in x.relative_to(p).parts)]))'
 for name in json.loads(remote('python3 -c '+shlex.quote(code))):
  target=dest/name;target.parent.mkdir(exist_ok=True,parents=True)
  subprocess.run(['scp','-O','-q','tsps:/mnt/UDISK/roadmap-v2-'+label+'/'+name,str(target)],check=True)
 for name in ('title','world','right','left','map','return','pause','unpause'):
  path='/mnt/UDISK/wol-goal-20261015/'+label+'-'+name+'.png'
  if remote('test -f '+shlex.quote(path)+' && printf yes || true').strip()=='yes':
   subprocess.run(['scp','-O','-q','tsps:'+path,str(dest/(name+'.png'))],check=True)
 subprocess.run(['scp','-O','-q','tsps:/mnt/UDISK/'+label+'-run.log',str(dest/'host-run.log')],check=True)
 print('COLLECTED',label,'failure',r.get('failure'),flush=True)
 assert not r.get('failure') and not r.get('cleanup_warnings') and r.get('runtime_sha256')==expected,r

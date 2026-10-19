#!/usr/bin/env python3
"""Host runner for one exact owned device probe; preserves failed-trial artifacts."""
from pathlib import Path
import argparse
import hashlib
import json
import shlex
import subprocess
import time


def main():
    repo=Path(__file__).resolve().parent.parent
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('label')
    ap.add_argument('--elf',required=True)
    ap.add_argument('--layout',required=True)
    ap.add_argument('--out',type=Path,required=True)
    ap.add_argument('--env',required=True)
    ap.add_argument('--probe-args',default='')
    ap.add_argument('--ssh-target',default='tsps')
    a=ap.parse_args();label=a.label
    if not label.replace('-','').isalnum():ap.error('simple label required')
    if len(a.elf)!=64 or any(c not in '0123456789abcdef' for c in a.elf):ap.error('exact lowercase SHA256 required')
    env=json.loads(a.env)
    if not all(k.startswith(('WOL_','T2_')) and isinstance(v,str) for k,v in env.items()):
        ap.error('explicit WOL_/T2_ environment string values required')
    ssh=['ssh','-o','ControlMaster=no','-o','ControlPath=none','-o','BatchMode=yes','-o','ConnectTimeout=15',a.ssh_target]
    def remote(command):
        return subprocess.run(ssh+[command],text=True,capture_output=True,check=True,timeout=80).stdout
    if remote('sha256sum /mnt/SDCARD/Roms/PORTS/wol-switch/wol-horizon').split()[0]!=a.elf:
        raise RuntimeError('installed ELF differs')
    probe_sha=hashlib.sha256((repo/'tools/wol_roadmap_probe.py').read_bytes()).hexdigest()
    if remote('sha256sum /mnt/UDISK/wol_roadmap_probe.py').split()[0]!=probe_sha:
        raise RuntimeError('installed probe differs')
    if remote('test -d /mnt/UDISK/roadmap-v2-%s && printf yes || true'%label).strip():
        raise RuntimeError('refuse to reuse trial directory')
    dest=a.out/label
    if dest.exists():raise RuntimeError('refuse to overwrite host trial')
    args=['env',*(k+'='+v for k,v in env.items()),'python3','/mnt/UDISK/wol_roadmap_probe.py',
          '--label',label,'--layout',a.layout,'--present-watchdog','30','--stall-gdb',*shlex.split(a.probe_args)]
    remote('setsid nohup '+shlex.join(args)+' > /mnt/UDISK/'+label+'-run.log 2>&1 < /dev/null &')
    print('STARTED',label,flush=True)
    deadline=time.monotonic()+1000
    while time.monotonic()<deadline:
        code='from pathlib import Path;p=Path("/mnt/UDISK/roadmap-v2-'+label+'/receipt.json");print(p.read_text() if p.exists() else "{}")'
        r=json.loads(remote('python3 -c '+shlex.quote(code)))
        if 'cleanup_warnings' in r:break
        time.sleep(10)
    else:raise RuntimeError(label+' incomplete; backup preserved; inspect exact owned PID, never blindly kill')
    dest.mkdir(parents=True,exist_ok=False)
    code='from pathlib import Path;import json;p=Path("/mnt/UDISK/roadmap-v2-'+label+'");print(json.dumps([str(x.relative_to(p)) for x in p.rglob("*") if x.is_file() and (x.name in ("receipt.json","effective-env.json","ledger.jsonl","runtime.log.gz","restored-menu.png") or x.name.startswith("sdk-heap-") or "stall" in x.relative_to(p).parts)]))'
    for name in json.loads(remote('python3 -c '+shlex.quote(code))):
        target=dest/name;target.parent.mkdir(exist_ok=True,parents=True)
        subprocess.run(['scp','-O','-q',a.ssh_target+':/mnt/UDISK/roadmap-v2-'+label+'/'+name,str(target)],check=True,timeout=120)
    code='from pathlib import Path;import json;print(json.dumps([p.name for p in Path("/mnt/UDISK/wol-goal-20261015").glob("'+label+'-*") if p.suffix in (".png",".json")]))'
    for name in json.loads(remote('python3 -c '+shlex.quote(code))):
        subprocess.run(['scp','-O','-q',a.ssh_target+':/mnt/UDISK/wol-goal-20261015/'+name,str(dest/name[len(label)+1:])],check=True,timeout=120)
    for source,target in (('/mnt/UDISK/wol-goal-20261015/session.json','session.json'),('/mnt/UDISK/'+label+'-run.log','host-run.log')):
        subprocess.run(['scp','-O','-q',a.ssh_target+':'+source,str(dest/target)],check=True,timeout=120)
    print('COLLECTED',label,'failure',r.get('failure'),'warnings',r.get('cleanup_warnings'),flush=True)
    if not r.get('cleanup_verified') or r.get('cleanup_warnings') or r.get('runtime_sha256')!=a.elf:
        raise RuntimeError('trial cleanup/identity gate failed; preserved receipt '+str(dest/'receipt.json'))
    actual=json.loads((dest/'effective-env.json').read_text())
    if any(actual.get(k)!=v for k,v in env.items()):raise RuntimeError('effective environment differs')
    if r.get('failure'):raise RuntimeError('trial failed but artifacts preserved: '+str(r['failure']))
    print('ALL_DONE',label,flush=True)


if __name__=='__main__':main()

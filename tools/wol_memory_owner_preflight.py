#!/usr/bin/env python3
"""One owned memory-only route; bounded descriptor census, no page mutations."""
from pathlib import Path
import json,os,subprocess,sys,time
sys.path.insert(0,'/mnt/UDISK')
from wol_roadmap_probe import pids
from wol_memory_profile import Observer
label=sys.argv[1];assert label.replace('-','').isalnum()
assert not pids('wol-horizon') and len(pids('MainUI'))==1
root=Path('/mnt/UDISK')/('roadmap-v2-'+label)
env=dict(os.environ,WOL_UPLOAD_SKIP='0',WOL_UNIFORM_CACHE='0',WOL_COPY_EQUAL='0',WOL_ALLOC_TRACE='1',WOL_ROMFS_LIFETIME='1')
p=subprocess.Popen([sys.executable,'/mnt/UDISK/wol_roadmap_probe.py','--label',label,'--layout','/mnt/UDISK/uploadskip1-layout.json'],env=env)
layout=json.loads(Path('/mnt/UDISK/uploadskip1-layout.json').read_text())
seen=set();deadline=time.monotonic()+320
while p.poll() is None and time.monotonic()<deadline:
    phase=(root/'phase.txt').read_text().strip() if (root/'phase.txt').exists() else ''
    if phase in ('menu','game-idle','map','map-return') and phase not in seen:
        ps=pids('wol-horizon');assert len(ps)==1
        start=time.monotonic_ns();obs=Observer(ps[0],layout)
        data=obs.snapshot(phase,pages=False);data['snapshot_cost_ns']=time.monotonic_ns()-start
        (root/('descriptor-'+phase+'.json')).write_text(json.dumps(data,indent=2))
        seen.add(phase)
        print('DESCRIPTORS',phase,data['descriptors']['texture_objects'],flush=True)
    time.sleep(1)
rc=p.wait(timeout=40)
assert rc==0 and seen=={'menu','game-idle','map','map-return'},(rc,seen)
print('MEMORY_PREFLIGHT_FINISHED',flush=True)

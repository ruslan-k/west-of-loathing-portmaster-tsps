#!/usr/bin/env python3
"""One bounded GPU-governor A/B; restore exact device policy in finally."""
from pathlib import Path
import os,subprocess,sys,json
sys.path.insert(0,'/mnt/UDISK')
from wol_roadmap_probe import pids
root=Path('/sys/class/devfreq/1800000.gpu')
assert not pids('wol-horizon') and len(pids('MainUI'))==1,'refuse occupied device'
label=sys.argv[1]
assert label.replace('-','').isalnum()
out=Path('/mnt/UDISK')/(label+'-governor.json')
before={n:(root/n).read_text().strip() for n in ('governor','min_freq','max_freq')}
receipt: dict[str, object]=dict(before=before,requested_min_freq=before['max_freq'],cleanup=False)
out.write_text(json.dumps(receipt,indent=2))
try:
    # Firmware resets governor during startup; min-frequency alone is this arm.
    receipt['during']={n:(root/n).read_text().strip() for n in ('governor','min_freq','max_freq','cur_freq')}
    out.write_text(json.dumps(receipt,indent=2))
    env=dict(os.environ,WOL_UPLOAD_SKIP='0',WOL_UNIFORM_CACHE='0',WOL_COPY_EQUAL='0',WOL_COPY_AUDIT='0',WOL_MODE_TRACE='0')
    p=subprocess.Popen([sys.executable,'/mnt/UDISK/wol_roadmap_probe.py','--label',label,'--layout','/mnt/UDISK/uploadskip1-layout.json'],env=env)
    import time
    deadline=time.monotonic()+120
    while not pids('wol-horizon') and p.poll() is None and time.monotonic()<deadline:time.sleep(.2)
    assert len(pids('wol-horizon'))==1,'no owned runtime'
    # standard_launch resets devfreq before exec. Apply ONLY after runtime appears.
    (root/'min_freq').write_text(before['max_freq'])
    receipt['after_runtime_start']={n:(root/n).read_text().strip() for n in ('governor','min_freq','cur_freq')}
    out.write_text(json.dumps(receipt,indent=2))
    receipt['probe_exit']=p.wait(timeout=360)
finally:
    (root/'min_freq').write_text(before['min_freq'])
    (root/'governor').write_text(before['governor'])
    receipt['restored']={n:(root/n).read_text().strip() for n in before}
    receipt['cleanup']=receipt['restored']==before
    out.write_text(json.dumps(receipt,indent=2))
    print('GOVERNOR_RESTORED',json.dumps(receipt),flush=True)
assert receipt['cleanup'] and receipt.get('probe_exit')==0,receipt

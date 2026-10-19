#!/usr/bin/env python3
"""Build the ARM64 sparse-copy fixture with the pinned cross container and run it on an
idle owned TSPS device; publish raw transcript + hashes. No runtime change, no guest data."""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess

ROOT=Path(__file__).resolve().parent.parent
CONTAINER='pmjs-arm64-spruce-local:20261002-gcc10'
FIXTURE=ROOT/'tools/fixtures/t2_sparse_copy_fixture.c'
OUT=ROOT/'evidence/transfer-sparse-repeat'


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--ssh-target',default='tsps')
    ap.add_argument('--device-path',default='/mnt/UDISK/t2_sparse_copy_fixture.aarch64')
    ap.add_argument('--build-only',action='store_true')
    a=ap.parse_args()
    OUT.mkdir(parents=True,exist_ok=True)
    binary=OUT/'t2_sparse_copy_fixture.aarch64'
    source_sha=hashlib.sha256(FIXTURE.read_bytes()).hexdigest()
    rel=str(binary.relative_to(ROOT))
    script=('set -e\n'
            'cd /work\n'
            'if aarch64-linux-gnu-gcc -O1 -static -o "$1" tools/fixtures/t2_sparse_copy_fixture.c >/tmp/cc.log 2>&1; then\n'
            '  echo LINK=static\n'
            'else\n'
            '  cat /tmp/cc.log >&2\n'
            '  aarch64-linux-gnu-gcc -O1 -o "$1" tools/fixtures/t2_sparse_copy_fixture.c\n'
            '  echo LINK=dynamic\n'
            'fi\n'
            'aarch64-linux-gnu-strip "$1"\n'
            'sha256sum "$1"\n')
    build=subprocess.run(['docker','run','--rm','--security-opt','label=disable','-v',str(ROOT)+':/work',
        '--entrypoint','/bin/sh',CONTAINER,'-c',script,'sh',rel],capture_output=True,text=True)
    if build.returncode:raise SystemExit('cross build failed:\n'+build.stdout+build.stderr)
    linking='static' if 'LINK=static' in build.stdout else 'dynamic'
    built_sha=hashlib.sha256(binary.read_bytes()).hexdigest()
    print('BUILT',linking,built_sha,flush=True)
    if a.build_only:return
    ssh=['ssh','-o','ControlMaster=no','-o','ControlPath=none','-o','BatchMode=yes','-o','ConnectTimeout=15',a.ssh_target]
    pre='''from pathlib import Path
comms=[]
for p in Path('/proc').iterdir():
    if p.name.isdecimal():
        try:comms.append((p/'comm').read_text().strip())
        except OSError:pass
print(comms.count('wol-horizon'),comms.count('MainUI'))
print(Path('/proc/sys/kernel/osrelease').read_text().strip())
print(Path('/proc/meminfo').read_text().split('MemAvailable:')[1].split()[0])
'''
    state=subprocess.run(ssh+['python3 -'],input=pre,text=True,capture_output=True,check=True,timeout=60)
    games,menus,release,memavail=state.stdout.split()
    if games!='0' or menus!='1':
        raise SystemExit('device not idle (wol-horizon=%s MainUI=%s); never disturb an owned session'%(games,menus))
    subprocess.run(['scp','-O','-q',str(binary),a.ssh_target+':'+a.device_path],check=True,timeout=120)
    back=subprocess.run(ssh+['sha256sum '+a.device_path],text=True,capture_output=True,check=True,timeout=60).stdout.split()[0]
    if back!=built_sha:raise SystemExit('device binary hash mismatch')
    try:
        run=subprocess.run(ssh+[a.device_path+' device'],text=True,capture_output=True,timeout=300)
    finally:
        subprocess.run(ssh+['rm -f '+a.device_path],text=True,capture_output=True,timeout=60)
    (OUT/'device-fixture-run.txt').write_text(run.stdout+('\n[stderr]\n'+run.stderr if run.stderr else ''))
    rows={};rss={}
    for line in run.stdout.splitlines():
        parts=line.split()
        if line.startswith('CASE '):rows[parts[1]]=dict(p.split('=') for p in parts[2:])
        elif line.startswith('RSS '):rss[parts[1]]=dict(p.split('=') for p in parts[2:])
    summary=dict(schema=1,fixture_source_sha256=source_sha,binary_sha256=built_sha,linking=linking,
                 kernel=release,mem_available_kib=int(memavail),device_path=a.device_path,
                 exit_code=run.returncode,cases=rows,rss=rss,
                 caveat=('Synthetic ARM64 contract run on the idle device; proves the shipped scan '
                         'block and destination-commit behavior, not game adoption or game-page reclaim.'))
    (OUT/'device-fixture-run.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps(summary,indent=2),flush=True)
    if run.returncode:raise SystemExit('fixture failed on device')


if __name__=='__main__':main()
